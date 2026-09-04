"""Build and run the independent MPFI/C center-certificate verifier."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path

from minoverlap.baseline import artifact_sha256, compile_mpfi_verifier
from minoverlap.center_certificate import CENTER_SCHEMA, parse_center_certificate

_REQUIRED_FIELDS = frozenset(
    {
        "backend",
        "mpfi_version",
        "certificate_schema",
        "precision_bits",
        "initial_cells",
        "max_depth",
        "target",
        "cosine_rows",
        "parseval_order",
        "visited_cells",
        "negative_cells",
        "positive_cells",
        "split_cells",
        "terminal_cells",
        "max_depth_seen",
        "positive_antiderivative_upper",
        "uncertain_rectangle_upper",
        "denominator_upper",
        "target_denominator_exact",
        "target_denominator_lower",
        "denominator_margin_lower",
        "certified",
    }
)
_DECIMAL_FIELDS = (
    "positive_antiderivative_upper",
    "uncertain_rectangle_upper",
    "denominator_upper",
    "target_denominator_lower",
    "denominator_margin_lower",
)
_INTEGER_FIELDS = (
    "precision_bits",
    "initial_cells",
    "max_depth",
    "cosine_rows",
    "parseval_order",
    "visited_cells",
    "negative_cells",
    "positive_cells",
    "split_cells",
    "terminal_cells",
    "max_depth_seen",
)


def _decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"invalid decimal in MPFI output for {field}") from error
    if not parsed.is_finite():
        raise ValueError(f"non-finite decimal in MPFI output for {field}")
    return parsed


def _nonnegative_integer(value: str, field: str) -> int:
    if not value.isascii() or not value.isdigit():
        raise ValueError(f"invalid integer in MPFI output for {field}")
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"negative integer in MPFI output for {field}")
    return parsed


def parse_center_mpfi_output(output: str) -> dict[str, str]:
    """Parse and cross-check the stable key-value C verifier output."""

    fields: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            raise ValueError("MPFI output contains a non-field line")
        key, value = line.split("=", 1)
        if not key or key in fields:
            raise ValueError(f"MPFI output contains an invalid or duplicate field: {key}")
        fields[key] = value

    missing = _REQUIRED_FIELDS - fields.keys()
    if missing:
        raise ValueError(f"MPFI output is missing fields: {sorted(missing)}")
    if fields["backend"] != "mpfi-c":
        raise ValueError("unexpected MPFI verifier backend")
    if fields["certificate_schema"] != CENTER_SCHEMA:
        raise ValueError("unexpected MPFI certificate schema")
    if fields["certified"] != "true":
        raise ValueError("MPFI verifier did not certify the target")

    numeric = {field: _decimal(fields[field], field) for field in _DECIMAL_FIELDS}
    integers = {
        field: _nonnegative_integer(fields[field], field)
        for field in _INTEGER_FIELDS
    }
    if numeric["positive_antiderivative_upper"] < 0:
        raise ValueError("MPFI positive-antiderivative upper bound is negative")
    if numeric["uncertain_rectangle_upper"] < 0:
        raise ValueError("MPFI uncertain-rectangle upper bound is negative")
    if numeric["denominator_upper"] <= 0:
        raise ValueError("MPFI denominator upper bound is not positive")
    if numeric["target_denominator_lower"] <= numeric["denominator_upper"]:
        raise ValueError("MPFI target comparison is not strict")
    if numeric["denominator_margin_lower"] <= 0:
        raise ValueError("MPFI denominator margin is not positive")
    if integers["max_depth_seen"] > integers["max_depth"]:
        raise ValueError("MPFI output reports a depth beyond its configured maximum")
    return fields


def run_center_mpfi(
    source: Path,
    certificate_path: Path,
    binary_path: Path,
    *,
    precision_bits: int = 256,
    initial_cells: int = 4_096,
    max_depth: int = 16,
    timeout_seconds: int = 7_200,
) -> dict[str, object]:
    """Compile and run the independent MPFI verifier."""

    try:
        payload = certificate_path.read_bytes()
    except OSError as error:
        raise ValueError("cannot read center certificate") from error
    certificate = parse_center_certificate(payload)
    certificate_hash = hashlib.sha256(payload).hexdigest()
    binary = compile_mpfi_verifier(source, binary_path)
    with tempfile.TemporaryFile(mode="w+b", dir=binary.parent) as certificate_copy:
        certificate_copy.write(payload)
        certificate_copy.flush()
        os.fsync(certificate_copy.fileno())
        certificate_copy.seek(0)
        descriptor = certificate_copy.fileno()
        try:
            completed = subprocess.run(
                [
                    str(binary),
                    f"/dev/fd/{descriptor}",
                    str(precision_bits),
                    str(initial_cells),
                    str(max_depth),
                ],
                check=False,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                pass_fds=(descriptor,),
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("MPFI center verification timed out") from error
    if completed.returncode != 0:
        raise RuntimeError(
            "MPFI center verification failed "
            f"with exit code {completed.returncode}:\n{completed.stderr}"
        )
    fields = parse_center_mpfi_output(completed.stdout)
    expected_target = Decimal(int(certificate.target.numerator)) / Decimal(
        int(certificate.target.denominator)
    )
    if Decimal(fields["target"]) != expected_target:
        raise ValueError("MPFI output target does not match the parsed certificate")
    return {
        "status": "pass",
        "source_sha256": artifact_sha256(source),
        "certificate_sha256": certificate_hash,
        "fields": fields,
    }


def center_mpfi_record(result: Mapping[str, object]) -> dict[str, object]:
    """Return a stable JSON-compatible MPFI verification record."""

    return dict(result)
