from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

import numpy as np

DATA_SHA256 = "c9fdb2881874c4797acca21be2ab4fcf7b7a43e75ed763ce1f17d17e269e7453"
VERIFIER_SHA256 = "a967d8dfd18456a80c79984c69eb28b88a7548bf001c505455f97808a704274d"
ROW_KEYS = tuple(f"lower_row_{index}_tsv" for index in range(4))
ROW_SHA256 = (
    "214a16dad78ed1903748634b1981b5a706c39a9cdfe2c761ba22ea3e421811f3",
    "498bc70020abbcb314e2d33db3568e59c40bbe889f827f3e53f101b7b5ed56a8",
    "d28cec137151a7ab16f91382c5e7c25cab4a3e3dc6cc5b4885e1d98e4f8462e8",
    "9077fdba3821e09f667cd1ddf1389654b6a5aae477df775bcf0c899de2f282fe",
)
ROW_RUNS = ((20, 14), (20, 12), (20, 14), (20, 14))
MEAN_INTERVALS = (
    (Fraction("0"), Fraction("0.00259038")),
    (Fraction("0.00259038"), Fraction("0.035")),
    (Fraction("0.035"), Fraction("0.065")),
    (Fraction("0.065"), Fraction("1")),
)
BASELINE_LOWER = Fraction("0.380552257389830222107376462494")
RELEASED_CLAIM = Fraction(380552, 1_000_000)
REQUIRED_OUTPUT_FIELDS = frozenset(
    {
        "total_positive_part_upper",
        "support_charge_upper",
        "quadratic_c0_lower",
        "quadratic_a1_lower",
        "quadratic_a2_lower",
        "budget_pass",
    }
)


def artifact_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_artifact_hashes(data_path: Path, verifier_path: Path) -> None:
    observed_data = artifact_sha256(data_path)
    observed_verifier = artifact_sha256(verifier_path)
    if observed_data != DATA_SHA256:
        raise ValueError(f"certificate bundle hash mismatch: {observed_data}")
    if observed_verifier != VERIFIER_SHA256:
        raise ValueError(f"MPFI verifier hash mismatch: {observed_verifier}")


def validate_mean_intervals(
    intervals: Sequence[tuple[Fraction, Fraction]],
) -> None:
    if not intervals:
        raise ValueError("mean intervals are empty")
    if intervals[0][0] != 0:
        raise ValueError("mean intervals must start at zero")

    previous_right = Fraction(0)
    for left, right in intervals:
        if left > previous_right:
            raise ValueError(f"gap in mean intervals before {left}")
        if left < previous_right:
            raise ValueError(f"overlap in mean intervals before {left}")
        if right <= left:
            raise ValueError(f"nonpositive mean interval: [{left}, {right}]")
        previous_right = right

    if previous_right != 1:
        raise ValueError("mean intervals must end at one")


def _decimal(token: str, field: str) -> Decimal:
    try:
        value = Decimal(token)
    except InvalidOperation as error:
        raise ValueError(f"invalid {field} decimal: {token}") from error
    if not value.is_finite():
        raise ValueError(f"non-finite {field}: {token}")
    return value


def validate_row_text(text: str) -> int:
    lines = [line.split() for line in text.splitlines() if line.strip()]
    if not lines or len(lines[0]) != 4:
        raise ValueError("row header must contain a0, a1, a2, and atom count")

    _decimal(lines[0][0], "a0")
    _decimal(lines[0][1], "a1")
    _decimal(lines[0][2], "a2")
    try:
        atom_count = int(lines[0][3])
    except ValueError as error:
        raise ValueError("atom count is not an integer") from error
    if atom_count <= 0:
        raise ValueError("atom count must be positive")
    if len(lines) != atom_count + 1:
        raise ValueError(f"row declares {atom_count} atoms but contains {len(lines) - 1}")

    for index, atom in enumerate(lines[1:]):
        if len(atom) != 3:
            raise ValueError(f"atom {index} must contain xi, alpha, and beta")
        _decimal(atom[0], f"atom {index} xi")
        alpha = _decimal(atom[1], f"atom {index} alpha")
        _decimal(atom[2], f"atom {index} beta")
        if alpha <= 0:
            raise ValueError(f"atom {index} alpha must be positive")
    return atom_count


def extract_rows(data_path: Path, output_dir: Path) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with np.load(data_path, allow_pickle=False) as bundle:
        if str(bundle["schema"]) != "autocorr-6.5-public-certificate-v1":
            raise ValueError(f"unexpected certificate schema: {bundle['schema']}")
        paths: list[Path] = []
        for index, (key, expected_hash) in enumerate(zip(ROW_KEYS, ROW_SHA256, strict=True)):
            payload = bundle[key].tobytes()
            observed_hash = hashlib.sha256(payload).hexdigest()
            if observed_hash != expected_hash:
                raise ValueError(f"row {index} hash mismatch: {observed_hash}")
            text = payload.decode("ascii")
            validate_row_text(text)
            path = output_dir / f"dual_row_{index}.tsv"
            path.write_bytes(payload)
            paths.append(path)
    return tuple(paths)


def _dependency_prefix(name: str) -> Path:
    explicit = os.environ.get(f"{name.upper()}_PREFIX")
    candidates = [
        Path(explicit) if explicit else None,
        Path("/opt/homebrew/opt") / name,
        Path("/usr/local/opt") / name,
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_dir():
            return candidate
    raise RuntimeError(f"cannot locate {name}; install it or set {name.upper()}_PREFIX")


def compile_mpfi_verifier(source: Path, output: Path) -> Path:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise RuntimeError("a C compiler is required")

    output.parent.mkdir(parents=True, exist_ok=True)
    base_command = [
        compiler,
        "-O3",
        "-std=c11",
        str(source),
        "-lmpfi",
        "-lmpfr",
        "-lgmp",
        "-lm",
        "-o",
        str(output),
    ]
    system_attempt = subprocess.run(
        base_command,
        check=False,
        text=True,
        capture_output=True,
    )
    if system_attempt.returncode == 0:
        return output

    mpfi = _dependency_prefix("mpfi")
    mpfr = _dependency_prefix("mpfr")
    gmp = _dependency_prefix("gmp")
    prefixes = (mpfi, mpfr, gmp)
    include_flags = [f"-I{prefix / 'include'}" for prefix in prefixes]
    link_flags = [
        flag
        for prefix in prefixes
        for flag in (f"-L{prefix / 'lib'}", f"-Wl,-rpath,{prefix / 'lib'}")
    ]
    fallback_command = [
        *base_command[:3],
        *include_flags,
        *base_command[3:4],
        *link_flags,
        *base_command[4:],
    ]
    fallback_attempt = subprocess.run(
        fallback_command,
        check=False,
        text=True,
        capture_output=True,
    )
    if fallback_attempt.returncode == 0:
        return output

    raise RuntimeError(
        "MPFI verifier compilation failed with the system and explicit-prefix toolchains:\n"
        f"system:\n{system_attempt.stderr}\n"
        f"explicit prefixes:\n{fallback_attempt.stderr}"
    )


def parse_verifier_output(output: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if " " not in key:
            if key in fields:
                raise ValueError(f"verifier output repeats field: {key}")
            fields[key] = value
    missing = REQUIRED_OUTPUT_FIELDS - fields.keys()
    if missing:
        raise ValueError(f"verifier output missing fields: {sorted(missing)}")
    if fields["budget_pass"] != "true":
        raise ValueError(
            f"positive-part budget did not pass: {fields['total_positive_part_upper']}"
        )
    numeric = {
        key: _decimal(fields[key], key)
        for key in REQUIRED_OUTPUT_FIELDS
        if key != "budget_pass"
    }
    total = numeric["total_positive_part_upper"]
    if total < 0 or total > 1:
        raise ValueError(f"total_positive_part_upper is outside [0, 1]: {total}")
    if numeric["support_charge_upper"] < 0:
        raise ValueError(
            f"support_charge_upper is negative: {numeric['support_charge_upper']}"
        )
    return fields


def run_mpfi_row(
    binary: Path,
    row_path: Path,
    initial_cells: int,
    max_depth: int,
    timeout_seconds: int = 7200,
) -> dict[str, str]:
    try:
        row_text = row_path.read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read verifier row: {row_path}") from error
    validate_row_text(row_text)

    completed = subprocess.run(
        [str(binary), str(row_path), str(initial_cells), str(max_depth)],
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"row verification failed with exit code {completed.returncode}:\n{completed.stderr}"
        )
    return parse_verifier_output(completed.stdout)


def row_quadratic(fields: Mapping[str, str], mean: Fraction) -> Fraction:
    c0 = Fraction(fields["quadratic_c0_lower"])
    a1 = Fraction(fields["quadratic_a1_lower"])
    a2 = Fraction(fields["quadratic_a2_lower"])
    return c0 + a1 * mean + a2 * mean * mean / 2


def certified_global_lower(
    rows: Sequence[Mapping[str, str]],
    intervals: Sequence[tuple[Fraction, Fraction]],
) -> Fraction:
    validate_mean_intervals(intervals)
    if len(rows) != len(intervals):
        raise ValueError("verified row count does not match mean interval count")

    floors: list[Fraction] = []
    for index, (fields, (left, right)) in enumerate(zip(rows, intervals, strict=True)):
        a2 = Fraction(fields["quadratic_a2_lower"])
        if a2 >= 0:
            raise ValueError(f"row {index} is not concave")
        floors.append(min(row_quadratic(fields, left), row_quadratic(fields, right)))
    return min(floors)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def audit_baseline(root: Path | None = None) -> dict[str, object]:
    root = root or project_root()
    station = root / "upstream" / "station"
    data_path = station / "autocorr_6_5_certificate_data.npz"
    verifier_path = station / "mpfi_positive_budget.c"
    validate_artifact_hashes(data_path, verifier_path)
    validate_mean_intervals(MEAN_INTERVALS)
    row_dir = root / "generated" / "rows"
    rows = extract_rows(data_path, row_dir)
    return {
        "status": "pass",
        "data_sha256": DATA_SHA256,
        "verifier_sha256": VERIFIER_SHA256,
        "row_sha256": list(ROW_SHA256),
        "atom_counts": [validate_row_text(path.read_text()) for path in rows],
    }


def verify_baseline(
    root: Path | None = None,
    selected_rows: Sequence[int] | None = None,
) -> dict[str, object]:
    root = root or project_root()
    audit = audit_baseline(root)
    station = root / "upstream" / "station"
    binary = compile_mpfi_verifier(
        station / "mpfi_positive_budget.c",
        root / "generated" / "bin" / "mpfi_positive_budget",
    )
    row_paths = tuple(root / "generated" / "rows" / f"dual_row_{index}.tsv" for index in range(4))
    indexes = tuple(selected_rows) if selected_rows is not None else tuple(range(4))
    if any(index not in range(4) for index in indexes):
        raise ValueError("row index must be between 0 and 3")

    verified: dict[int, dict[str, str]] = {}
    for index in indexes:
        initial_cells, max_depth = ROW_RUNS[index]
        verified[index] = run_mpfi_row(
            binary,
            row_paths[index],
            initial_cells,
            max_depth,
        )

    result: dict[str, object] = {
        **audit,
        "verified_rows": verified,
        "python": sys.version.split()[0],
    }
    if indexes == tuple(range(4)):
        ordered_rows = tuple(verified[index] for index in range(4))
        global_lower = certified_global_lower(ordered_rows, MEAN_INTERVALS)
        if global_lower < BASELINE_LOWER:
            raise ValueError(f"global lower bound is below the pinned baseline: {global_lower}")
        result["certified_global_lower"] = str(global_lower)
        result["margin_above_released_claim"] = str(global_lower - RELEASED_CLAIM)
        result["margin_above_pinned_baseline"] = str(global_lower - BASELINE_LOWER)
    return result
