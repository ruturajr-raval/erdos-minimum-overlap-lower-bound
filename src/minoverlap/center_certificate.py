"""Rigorous verification for the project center-bin certificate."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from flint import arb, ctx, fmpq

CENTER_SCHEMA = "minimum-overlap-center-certificate-v1"
_DECIMAL_RE = re.compile(rb"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z")
_INTEGER_RE = re.compile(rb"(?:0|[1-9][0-9]*)\Z")
_MAX_DECIMAL_BYTES = 128
_MAX_COSINE_ROWS = 512
_MAX_PARSEVAL_ORDER = 1_000
_MAX_FREQUENCY = fmpq(10_000)


class CenterCertificateError(ValueError):
    """The center certificate is malformed or violates its schema."""


class CenterVerificationError(RuntimeError):
    """The directed-arithmetic proof could not certify the requested target."""


@dataclass(frozen=True, slots=True)
class CosineRow:
    frequency: fmpq
    multiplier: fmpq


@dataclass(frozen=True, slots=True)
class CenterCertificate:
    target: fmpq
    mean_abs_max: fmpq
    second_moment_multiplier: fmpq
    parseval_order: int
    parseval_multiplier: fmpq
    cosine_rows: tuple[CosineRow, ...]


@dataclass(frozen=True, slots=True)
class CenterCellAudit:
    negative_cells: int
    positive_cells: int
    split_cells: int
    terminal_cells: int
    max_depth_seen: int


@dataclass(frozen=True, slots=True)
class CenterVerification:
    certificate_sha256: str
    precision_bits: int
    initial_cells: int
    max_depth: int
    cosine_rows: int
    parseval_order: int
    positive_antiderivative_upper: fmpq
    uncertain_rectangle_upper: fmpq
    denominator_upper: fmpq
    target_denominator: fmpq
    denominator_margin: fmpq
    target: fmpq
    audit: CenterCellAudit

    @property
    def certified(self) -> bool:
        return self.denominator_margin > 0


@dataclass(frozen=True, slots=True)
class _Term:
    frequency: arb
    coefficient: arb
    derivative_coefficient: arb
    second_derivative_coefficient: arb
    primitive_coefficient: arb


@dataclass(frozen=True, slots=True)
class _CompiledCertificate:
    constant: arb
    quadratic: arb
    terms: tuple[_Term, ...]
    third_derivative_bound: arb


def _parse_decimal(token: bytes, field: str) -> fmpq:
    if len(token) > _MAX_DECIMAL_BYTES or _DECIMAL_RE.fullmatch(token) is None:
        raise CenterCertificateError(f"invalid canonical decimal for {field}")
    whole, dot, fractional = token.partition(b".")
    numerator = int(whole + fractional)
    denominator = 10 ** len(fractional) if dot else 1
    return fmpq(numerator, denominator)


def _parse_integer(token: bytes, field: str) -> int:
    if _INTEGER_RE.fullmatch(token) is None:
        raise CenterCertificateError(f"invalid canonical integer for {field}")
    return int(token)


def parse_center_certificate(payload: bytes | str) -> CenterCertificate:
    """Parse the canonical line-oriented center-certificate format."""

    if isinstance(payload, str):
        try:
            payload = payload.encode("ascii")
        except UnicodeEncodeError as error:
            raise CenterCertificateError("certificate is not ASCII") from error
    if not payload.endswith(b"\n") or b"\r" in payload or b"\0" in payload:
        raise CenterCertificateError("certificate must be canonical LF-terminated ASCII")

    lines = payload[:-1].split(b"\n")
    if len(lines) < 8 or any(not line for line in lines):
        raise CenterCertificateError("certificate is incomplete or contains an empty line")
    if lines[0] != CENTER_SCHEMA.encode("ascii"):
        raise CenterCertificateError("unexpected center-certificate schema")

    def field(index: int, expected_name: bytes) -> bytes:
        parts = lines[index].split(b"\t")
        if len(parts) != 2 or parts[0] != expected_name:
            raise CenterCertificateError(
                f"line {index + 1} must contain {expected_name.decode('ascii')}"
            )
        return parts[1]

    target = _parse_decimal(field(1, b"target"), "target")
    mean_abs_max = _parse_decimal(field(2, b"mean_abs_max"), "mean_abs_max")
    second_moment_multiplier = _parse_decimal(
        field(3, b"second_moment_multiplier"),
        "second_moment_multiplier",
    )
    parseval_order = _parse_integer(field(4, b"parseval_order"), "parseval_order")
    parseval_multiplier = _parse_decimal(
        field(5, b"parseval_multiplier"),
        "parseval_multiplier",
    )
    cosine_count = _parse_integer(field(6, b"cosine_count"), "cosine_count")

    if not 0 < target < 1:
        raise CenterCertificateError("target must lie strictly between zero and one")
    if mean_abs_max != fmpq(1, 320):
        raise CenterCertificateError("mean_abs_max must equal 1/320")
    if second_moment_multiplier <= 0:
        raise CenterCertificateError("second-moment multiplier must be positive")
    if not 1 <= parseval_order <= _MAX_PARSEVAL_ORDER:
        raise CenterCertificateError("parseval order is outside the accepted range")
    if parseval_multiplier <= 0:
        raise CenterCertificateError("Parseval multiplier must be positive")
    if not 1 <= cosine_count <= _MAX_COSINE_ROWS:
        raise CenterCertificateError("cosine count is outside the accepted range")
    if len(lines) != 7 + cosine_count:
        raise CenterCertificateError(
            f"certificate declares {cosine_count} cosine rows but contains "
            f"{len(lines) - 7}"
        )

    cosine_rows: list[CosineRow] = []
    previous_frequency = fmpq(0)
    for index, line in enumerate(lines[7:]):
        parts = line.split(b"\t")
        if len(parts) != 3 or parts[0] != b"cosine":
            raise CenterCertificateError(f"invalid cosine row at index {index}")
        frequency = _parse_decimal(parts[1], f"cosine {index} frequency")
        multiplier = _parse_decimal(parts[2], f"cosine {index} multiplier")
        if not previous_frequency < frequency <= _MAX_FREQUENCY:
            raise CenterCertificateError(
                "cosine frequencies must be positive, bounded, and strictly increasing"
            )
        if multiplier <= 0:
            raise CenterCertificateError(f"cosine {index} multiplier must be positive")
        cosine_rows.append(CosineRow(frequency, multiplier))
        previous_frequency = frequency

    return CenterCertificate(
        target=target,
        mean_abs_max=mean_abs_max,
        second_moment_multiplier=second_moment_multiplier,
        parseval_order=parseval_order,
        parseval_multiplier=parseval_multiplier,
        cosine_rows=tuple(cosine_rows),
    )


def load_center_certificate(path: Path) -> tuple[CenterCertificate, str]:
    """Read and hash a center certificate before parsing it."""

    try:
        payload = path.read_bytes()
    except OSError as error:
        raise CenterCertificateError("cannot read center certificate") from error
    return parse_center_certificate(payload), hashlib.sha256(payload).hexdigest()


def _term(frequency: arb, coefficient: arb) -> _Term:
    return _Term(
        frequency=frequency,
        coefficient=coefficient,
        derivative_coefficient=-(coefficient * frequency),
        second_derivative_coefficient=-(coefficient * frequency * frequency),
        primitive_coefficient=coefficient / frequency,
    )


def _compile_certificate(certificate: CenterCertificate) -> _CompiledCertificate:
    second_multiplier = arb(certificate.second_moment_multiplier)
    parseval_multiplier = arb(certificate.parseval_multiplier)
    second_moment_bound = arb(
        fmpq(2, 3) + certificate.mean_abs_max * certificate.mean_abs_max / 2
    )
    constant = arb(1) + second_multiplier * second_moment_bound + parseval_multiplier / 2
    quadratic = -second_multiplier
    terms: list[_Term] = []
    third_derivative_bound = arb(0)

    for row in certificate.cosine_rows:
        frequency = arb(row.frequency)
        multiplier = arb(row.multiplier)
        sinc = frequency.sin() / frequency
        constant += multiplier * sinc * sinc
        term = _term(frequency, -multiplier)
        terms.append(term)
        third_derivative_bound += abs(term.coefficient) * frequency**3

    pi = arb.pi()
    for index in range(1, certificate.parseval_order + 1):
        frequency = pi * index
        term = _term(frequency, parseval_multiplier)
        terms.append(term)
        third_derivative_bound += abs(term.coefficient) * frequency**3

    if not constant.is_finite() or not third_derivative_bound.is_finite():
        raise CenterVerificationError("certificate compilation produced a non-finite value")
    return _CompiledCertificate(
        constant=constant,
        quadratic=quadratic,
        terms=tuple(terms),
        third_derivative_bound=third_derivative_bound,
    )


def _evaluate(
    certificate: _CompiledCertificate,
    x: arb,
) -> tuple[arb, arb, arb]:
    x_squared = x * x
    value = certificate.constant + certificate.quadratic * x_squared
    derivative = 2 * certificate.quadratic * x
    second_derivative = 2 * certificate.quadratic
    for term in certificate.terms:
        argument = term.frequency * x
        sine = argument.sin()
        cosine = argument.cos()
        value += term.coefficient * cosine
        derivative += term.derivative_coefficient * sine
        second_derivative += term.second_derivative_coefficient * cosine
    return value, derivative, second_derivative


def _endpoint(value: arb, *, upper: bool) -> fmpq:
    if not value.is_finite():
        raise CenterVerificationError("cannot extract an endpoint from a non-finite Arb ball")
    endpoint = value.upper() if upper else value.lower()
    if not endpoint.is_exact():
        raise CenterVerificationError("Arb did not return an exact dyadic endpoint")
    mantissa, exponent = endpoint.man_exp()
    if exponent >= 0:
        return fmpq(mantissa << exponent)
    return fmpq(mantissa, 1 << (-exponent))


def _taylor_range(
    certificate: _CompiledCertificate,
    left: fmpq,
    right: fmpq,
) -> arb:
    midpoint = (left + right) / 2
    radius = (right - left) / 2
    value, derivative, second_derivative = _evaluate(certificate, arb(midpoint))
    radius_ball = arb(radius)
    error = (
        abs(derivative) * radius_ball
        + abs(second_derivative) * radius_ball * radius_ball / 2
        + certificate.third_derivative_bound * radius_ball**3 / 6
    )
    enclosure = value + arb(0, _endpoint(error, upper=True))
    if not enclosure.is_finite():
        raise CenterVerificationError("Taylor enclosure is non-finite")
    return enclosure


def _antiderivative(certificate: _CompiledCertificate, x_value: fmpq) -> arb:
    x = arb(x_value)
    result = (
        certificate.constant * x
        + certificate.quadratic * x * x * x / 3
    )
    for term in certificate.terms:
        result += term.primitive_coefficient * (term.frequency * x).sin()
    if not result.is_finite():
        raise CenterVerificationError("antiderivative enclosure is non-finite")
    return result


def verify_center_certificate(
    path: Path,
    *,
    precision_bits: int = 256,
    initial_cells: int = 4_096,
    max_depth: int = 16,
) -> CenterVerification:
    """Certify the center-bin target using Python-flint Arb arithmetic."""

    if type(precision_bits) is not int or not 128 <= precision_bits <= 4_096:
        raise ValueError("precision_bits must be an integer from 128 through 4096")
    if type(initial_cells) is not int or not 1 <= initial_cells <= 65_536:
        raise ValueError("initial_cells must be a positive integer")
    if type(max_depth) is not int or not 0 <= max_depth <= 30:
        raise ValueError("max_depth must be an integer from zero through 30")

    certificate, certificate_hash = load_center_certificate(path)
    with ctx.workprec(precision_bits):
        compiled = _compile_certificate(certificate)
        positive_integral = arb(0)
        uncertain_integral = arb(0)
        pending_left: fmpq | None = None
        pending_right: fmpq | None = None
        negative_cells = 0
        positive_cells = 0
        split_cells = 0
        terminal_cells = 0
        max_depth_seen = 0

        def flush_positive_run() -> None:
            nonlocal pending_left, pending_right, positive_integral
            if pending_left is None or pending_right is None:
                return
            contribution = _antiderivative(compiled, pending_right) - _antiderivative(
                compiled, pending_left
            )
            if contribution.upper() < 0:
                raise CenterVerificationError(
                    "a certified-positive run has a negative integral"
                )
            positive_integral += contribution
            pending_left = None
            pending_right = None

        def extend_positive_run(left: fmpq, right: fmpq) -> None:
            nonlocal pending_left, pending_right
            if pending_left is None:
                pending_left = left
                pending_right = right
                return
            if pending_right != left:
                flush_positive_run()
                pending_left = left
            pending_right = right

        for initial_index in range(initial_cells):
            initial_left = fmpq(2 * initial_index, initial_cells)
            initial_right = fmpq(2 * (initial_index + 1), initial_cells)
            stack: list[tuple[fmpq, fmpq, int]] = [
                (initial_left, initial_right, 0)
            ]
            while stack:
                left, right, depth = stack.pop()
                enclosure = _taylor_range(compiled, left, right)
                if enclosure.upper() <= 0:
                    flush_positive_run()
                    negative_cells += 1
                elif enclosure.lower() >= 0:
                    positive_cells += 1
                    extend_positive_run(left, right)
                elif depth >= max_depth:
                    flush_positive_run()
                    terminal_cells += 1
                    upper = _endpoint(enclosure, upper=True)
                    if upper > 0:
                        uncertain_integral += arb(right - left) * arb(upper)
                else:
                    midpoint = (left + right) / 2
                    next_depth = depth + 1
                    split_cells += 1
                    max_depth_seen = max(max_depth_seen, next_depth)
                    stack.append((midpoint, right, next_depth))
                    stack.append((left, midpoint, next_depth))

        flush_positive_run()
        positive_upper = 2 * _endpoint(positive_integral, upper=True)
        uncertain_upper = 2 * _endpoint(uncertain_integral, upper=True)
        denominator_upper = positive_upper + uncertain_upper
        target_denominator = 1 / certificate.target
        margin = target_denominator - denominator_upper
        if margin <= 0:
            raise CenterVerificationError(
                "center certificate does not establish its declared target: "
                f"D_upper={denominator_upper}, 1/target={target_denominator}"
            )

        return CenterVerification(
            certificate_sha256=certificate_hash,
            precision_bits=precision_bits,
            initial_cells=initial_cells,
            max_depth=max_depth,
            cosine_rows=len(certificate.cosine_rows),
            parseval_order=certificate.parseval_order,
            positive_antiderivative_upper=positive_upper,
            uncertain_rectangle_upper=uncertain_upper,
            denominator_upper=denominator_upper,
            target_denominator=target_denominator,
            denominator_margin=margin,
            target=certificate.target,
            audit=CenterCellAudit(
                negative_cells=negative_cells,
                positive_cells=positive_cells,
                split_cells=split_cells,
                terminal_cells=terminal_cells,
                max_depth_seen=max_depth_seen,
            ),
        )


def center_verification_record(result: CenterVerification) -> dict[str, object]:
    """Convert an Arb verification result to a stable JSON record."""

    return {
        "backend": "python-flint Arb",
        "certificate_sha256": result.certificate_sha256,
        "precision_bits": result.precision_bits,
        "initial_cells": result.initial_cells,
        "max_depth": result.max_depth,
        "cosine_rows": result.cosine_rows,
        "parseval_order": result.parseval_order,
        "positive_antiderivative_upper": str(result.positive_antiderivative_upper),
        "uncertain_rectangle_upper": str(result.uncertain_rectangle_upper),
        "denominator_upper": str(result.denominator_upper),
        "target_denominator": str(result.target_denominator),
        "denominator_margin": str(result.denominator_margin),
        "target": str(result.target),
        "certified": result.certified,
        "audit": {
            "negative_cells": result.audit.negative_cells,
            "positive_cells": result.audit.positive_cells,
            "split_cells": result.audit.split_cells,
            "terminal_cells": result.audit.terminal_cells,
            "max_depth_seen": result.audit.max_depth_seen,
        },
    }
