"""Independent Python-Arb replay of the licensed Station dual rows.

The mathematical row formula and Taylor enclosure are part of the Station
certificate.  This module independently implements the parser, adaptive cover,
Arb evaluation, accounting, and result extraction without calling NumPy or the
MPFI reference verifier.
"""

from __future__ import annotations

import hashlib
import re
import struct
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from flint import arb, ctx, fmpq

STATION_BUNDLE_SHA256 = "c9fdb2881874c4797acca21be2ab4fcf7b7a43e75ed763ce1f17d17e269e7453"
STATION_ROW_SHA256 = (
    "214a16dad78ed1903748634b1981b5a706c39a9cdfe2c761ba22ea3e421811f3",
    "498bc70020abbcb314e2d33db3568e59c40bbe889f827f3e53f101b7b5ed56a8",
    "d28cec137151a7ab16f91382c5e7c25cab4a3e3dc6cc5b4885e1d98e4f8462e8",
    "9077fdba3821e09f667cd1ddf1389654b6a5aae477df775bcf0c899de2f282fe",
)
STATION_ROW_RUNS = ((20, 14), (20, 12), (20, 14), (20, 14))
STATION_MEAN_INTERVALS = (
    (fmpq(0), fmpq(129519, 50_000_000)),
    (fmpq(129519, 50_000_000), fmpq(7, 200)),
    (fmpq(7, 200), fmpq(13, 200)),
    (fmpq(13, 200), fmpq(1)),
)
STATION_RELEASED_CLAIM = fmpq(47_569, 125_000)

_DECIMAL_RE = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
_COUNT_RE = re.compile(rb"(?:0|[1-9][0-9]*)\Z")
_NPY_U1_HEADER_RE = re.compile(
    rb"\{'descr': '\|u1', 'fortran_order': False, "
    rb"'shape': \(([0-9]+),\), \} +\n\Z"
)
_MAX_DECIMAL_BYTES = 128
_MAX_DECIMAL_EXPONENT = 10_000
_MAX_ATOMS = 100_000
_MAX_NPY_BYTES = 16 * 1024 * 1024
_GUARD = fmpq(1, 500_000_000_000)


class CertificateFormatError(ValueError):
    """The serialized certificate is malformed or unauthenticated."""


class VerificationError(RuntimeError):
    """The interval proof could not certify the requested row."""


class BudgetVerificationError(VerificationError):
    """The rigorous positive-part upper bound exceeds the unit budget."""

    def __init__(self, upper: fmpq) -> None:
        self.upper = upper
        super().__init__(f"positive-part budget exceeds one: upper={upper}")


@dataclass(frozen=True, slots=True)
class DualAtom:
    xi: fmpq
    alpha: fmpq
    beta: fmpq


@dataclass(frozen=True, slots=True)
class DualRow:
    a0: fmpq
    a1: fmpq
    a2: fmpq
    atoms: tuple[DualAtom, ...]


@dataclass(frozen=True, slots=True)
class CellAudit:
    negative_cells: int
    positive_cells: int
    split_cells: int
    terminal_cells: int
    max_depth_seen: int


@dataclass(frozen=True, slots=True)
class RowVerification:
    atom_count: int
    precision_bits: int
    initial_cells: int
    max_depth: int
    positive_antiderivative_upper: fmpq
    uncertain_rectangle_upper: fmpq
    total_positive_part_upper: fmpq
    support_charge_upper: fmpq
    quadratic_c0_lower: fmpq
    quadratic_a1_lower: fmpq
    quadratic_a2_lower: fmpq
    audit: CellAudit

    @property
    def budget_pass(self) -> bool:
        return self.total_positive_part_upper <= 1


@dataclass(frozen=True, slots=True)
class BaselineVerification:
    rows: tuple[RowVerification, ...]
    certified_global_lower: fmpq
    margin_above_released_claim: fmpq


@dataclass(frozen=True, slots=True)
class _ArbAtom:
    xi: arb
    alpha: arb
    beta: arb
    alpha_xi: arb
    beta_xi: arb
    antiderivative_alpha: arb | None
    antiderivative_beta: arb | None


@dataclass(frozen=True, slots=True)
class _ArbRow:
    a0: arb
    a1: arb
    a2: arb
    atoms: tuple[_ArbAtom, ...]
    second_derivative_bound: fmpq


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_decimal(token: bytes, field: str) -> fmpq:
    if len(token) > _MAX_DECIMAL_BYTES or not _DECIMAL_RE.fullmatch(token):
        raise CertificateFormatError(f"invalid {field} decimal")

    mantissa, marker, exponent_text = token.lower().partition(b"e")
    exponent = int(exponent_text) if marker else 0
    if abs(exponent) > _MAX_DECIMAL_EXPONENT:
        raise CertificateFormatError(f"{field} exponent is too large")

    negative = mantissa.startswith(b"-")
    unsigned = mantissa[1:] if negative else mantissa
    whole, dot, fractional = unsigned.partition(b".")
    digits = whole + fractional
    numerator = int(digits)
    if negative:
        numerator = -numerator
    denominator = 10 ** len(fractional) if dot else 1
    if exponent >= 0:
        numerator *= 10**exponent
    else:
        denominator *= 10 ** (-exponent)
    return fmpq(numerator, denominator)


def parse_station_row(payload: bytes | str) -> DualRow:
    """Parse a canonical Station TSV row into exact rational coefficients."""

    if isinstance(payload, str):
        try:
            payload = payload.encode("ascii")
        except UnicodeEncodeError as error:
            raise CertificateFormatError("row is not ASCII") from error
    if not payload or not payload.endswith(b"\n"):
        raise CertificateFormatError("row must end with exactly one complete line")
    if b"\r" in payload or b"\0" in payload:
        raise CertificateFormatError("row contains a forbidden control byte")

    lines = payload[:-1].split(b"\n")
    if not lines or any(not line for line in lines):
        raise CertificateFormatError("row contains an empty line")

    header = lines[0].split(b"\t")
    if len(header) != 4:
        raise CertificateFormatError("row header must have four tab-separated fields")
    if not _COUNT_RE.fullmatch(header[3]):
        raise CertificateFormatError("atom count is not a canonical nonnegative integer")
    atom_count = int(header[3])
    if atom_count <= 0 or atom_count > _MAX_ATOMS:
        raise CertificateFormatError("atom count is outside the accepted range")
    if len(lines) != atom_count + 1:
        raise CertificateFormatError(
            f"row declares {atom_count} atoms but contains {len(lines) - 1}"
        )

    a0 = _parse_decimal(header[0], "a0")
    a1 = _parse_decimal(header[1], "a1")
    a2 = _parse_decimal(header[2], "a2")
    atoms: list[DualAtom] = []
    for index, line in enumerate(lines[1:]):
        fields = line.split(b"\t")
        if len(fields) != 3:
            raise CertificateFormatError(f"atom {index} must have three tab-separated fields")
        xi = _parse_decimal(fields[0], f"atom {index} xi")
        alpha = _parse_decimal(fields[1], f"atom {index} alpha")
        beta = _parse_decimal(fields[2], f"atom {index} beta")
        if alpha <= 0:
            raise CertificateFormatError(f"atom {index} alpha is not positive")
        atoms.append(DualAtom(xi=xi, alpha=alpha, beta=beta))
    return DualRow(a0=a0, a1=a1, a2=a2, atoms=tuple(atoms))


def _decode_npy_u1(blob: bytes) -> bytes:
    if len(blob) < 10 or blob[:6] != b"\x93NUMPY":
        raise CertificateFormatError("row member is not an NPY file")
    if blob[6:8] != b"\x01\x00":
        raise CertificateFormatError("only the canonical NPY v1 row encoding is accepted")

    header_length = struct.unpack_from("<H", blob, 8)[0]
    payload_offset = 10 + header_length
    if payload_offset > len(blob) or payload_offset % 16:
        raise CertificateFormatError("invalid NPY header length or alignment")
    header = blob[10:payload_offset]
    match = _NPY_U1_HEADER_RE.fullmatch(header)
    if match is None:
        raise CertificateFormatError("unexpected NPY row dtype, shape, or header")

    declared_size = int(match.group(1))
    payload = blob[payload_offset:]
    if declared_size != len(payload):
        raise CertificateFormatError(
            f"NPY row declares {declared_size} bytes but contains {len(payload)}"
        )
    return payload


def load_station_row(bundle_path: Path, row_index: int) -> DualRow:
    """Authenticate the Station bundle and load one row without NumPy."""

    if type(row_index) is not int or not 0 <= row_index < len(STATION_ROW_SHA256):
        raise CertificateFormatError("row index must be an integer from zero through three")
    try:
        observed_bundle_hash = _sha256(bundle_path)
    except OSError as error:
        raise CertificateFormatError("cannot read Station certificate bundle") from error
    if observed_bundle_hash != STATION_BUNDLE_SHA256:
        raise CertificateFormatError("Station certificate bundle hash mismatch")

    member_name = f"lower_row_{row_index}_tsv.npy"
    try:
        with zipfile.ZipFile(bundle_path) as archive:
            matches = [info for info in archive.infolist() if info.filename == member_name]
            if len(matches) != 1:
                raise CertificateFormatError(
                    f"expected exactly one archive member named {member_name}"
                )
            info = matches[0]
            if info.flag_bits & 1:
                raise CertificateFormatError("encrypted certificate members are not accepted")
            if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise CertificateFormatError("unsupported certificate compression method")
            if info.file_size > _MAX_NPY_BYTES:
                raise CertificateFormatError("certificate row member is too large")
            encoded_row = archive.read(info)
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise CertificateFormatError("cannot read Station certificate bundle") from error

    payload = _decode_npy_u1(encoded_row)
    observed_hash = hashlib.sha256(payload).hexdigest()
    if observed_hash != STATION_ROW_SHA256[row_index]:
        raise CertificateFormatError(f"Station row {row_index} hash mismatch")
    return parse_station_row(payload)


def _validate_row(row: DualRow) -> None:
    if not row.atoms or len(row.atoms) > _MAX_ATOMS:
        raise CertificateFormatError("row has an invalid atom count")
    if not all(isinstance(value, fmpq) for value in (row.a0, row.a1, row.a2)):
        raise CertificateFormatError("row coefficients must be exact fmpq values")
    for index, atom in enumerate(row.atoms):
        if not isinstance(atom, DualAtom):
            raise CertificateFormatError(f"atom {index} is not a DualAtom")
        if not all(isinstance(value, fmpq) for value in (atom.xi, atom.alpha, atom.beta)):
            raise CertificateFormatError(f"atom {index} coefficients must be exact fmpq values")
        if atom.alpha <= 0:
            raise CertificateFormatError(f"atom {index} alpha is not positive")


def _compile_row(row: DualRow) -> _ArbRow:
    atoms: list[_ArbAtom] = []
    second_derivative_bound = 2 * abs(row.a2)
    for atom in row.atoms:
        xi = arb(atom.xi)
        alpha = arb(atom.alpha)
        beta = arb(atom.beta)
        if atom.xi == 0:
            antiderivative_alpha = None
            antiderivative_beta = None
        else:
            antiderivative_alpha = arb(atom.alpha / atom.xi)
            antiderivative_beta = arb(atom.beta / atom.xi)
        atoms.append(
            _ArbAtom(
                xi=xi,
                alpha=alpha,
                beta=beta,
                alpha_xi=arb(atom.alpha * atom.xi),
                beta_xi=arb(atom.beta * atom.xi),
                antiderivative_alpha=antiderivative_alpha,
                antiderivative_beta=antiderivative_beta,
            )
        )
        second_derivative_bound += (abs(atom.alpha) + abs(atom.beta)) * atom.xi * atom.xi
    return _ArbRow(
        a0=arb(row.a0),
        a1=arb(row.a1),
        a2=arb(row.a2),
        atoms=tuple(atoms),
        second_derivative_bound=second_derivative_bound,
    )


def _evaluate_g_and_derivative(row: _ArbRow, x: arb) -> tuple[arb, arb]:
    x_squared = x * x
    value = row.a0 + row.a1 * x + row.a2 * x_squared
    derivative = row.a1 + 2 * row.a2 * x
    for atom in row.atoms:
        argument = atom.xi * x
        sine = argument.sin()
        cosine = argument.cos()
        value -= atom.alpha * cosine + atom.beta * sine
        derivative += atom.alpha_xi * sine - atom.beta_xi * cosine
    return value, derivative


def _taylor_range(row: _ArbRow, left: fmpq, right: fmpq) -> arb:
    midpoint = (left + right) / 2
    radius = (right - left) / 2
    value, derivative = _evaluate_g_and_derivative(row, arb(midpoint))
    delta = arb(0, radius)
    remainder_radius = row.second_derivative_bound * radius * radius / 2
    enclosure = value + derivative * delta + arb(0, remainder_radius)
    if not enclosure.is_finite():
        raise VerificationError("non-finite Taylor enclosure")
    return enclosure


def _antiderivative(row: _ArbRow, x_value: fmpq) -> arb:
    x = arb(x_value)
    x_squared = x * x
    result = row.a0 * x + row.a1 * x_squared / 2 + row.a2 * x_squared * x / 3
    for atom in row.atoms:
        if atom.antiderivative_alpha is None or atom.antiderivative_beta is None:
            result -= atom.alpha * x
            continue
        argument = atom.xi * x
        result -= atom.antiderivative_alpha * argument.sin()
        result += atom.antiderivative_beta * argument.cos()
    if not result.is_finite():
        raise VerificationError("non-finite antiderivative enclosure")
    return result


def _support_charge(row: DualRow, compiled: _ArbRow) -> arb:
    support = arb(0)
    for exact_atom, atom in zip(row.atoms, compiled.atoms, strict=True):
        sinc = arb(1) if exact_atom.xi == 0 else atom.xi.sin() / atom.xi
        gamma = arb(exact_atom.alpha + exact_atom.beta * exact_atom.beta / exact_atom.alpha)
        support += sinc * sinc * gamma
    if not support.is_finite():
        raise VerificationError("non-finite support-charge enclosure")
    return support


def _endpoint(value: arb, *, upper: bool) -> fmpq:
    if not value.is_finite():
        raise VerificationError("cannot extract an endpoint from a non-finite Arb ball")
    endpoint = value.upper() if upper else value.lower()
    if not endpoint.is_exact():
        raise VerificationError("Arb did not return an exact dyadic endpoint")
    mantissa, exponent = endpoint.man_exp()
    if exponent >= 0:
        return fmpq(mantissa << exponent)
    return fmpq(mantissa, 1 << (-exponent))


def verify_dual_row(
    row: DualRow,
    *,
    precision_bits: int = 192,
    initial_cells: int = 20,
    max_depth: int = 14,
    require_budget: bool = True,
) -> RowVerification:
    """Rigorously verify one dual row using Arb ball arithmetic.

    Certified-positive cells are merged and integrated with an Arb
    antiderivative. Certified-negative cells contribute zero. Every unresolved
    terminal cell is charged by ``width * max(sup(G), 0)``.
    """

    _validate_row(row)
    if type(precision_bits) is not int or not 128 <= precision_bits <= 4096:
        raise ValueError("precision_bits must be an integer from 128 through 4096")
    if type(initial_cells) is not int or not 1 <= initial_cells <= 1_000_000:
        raise ValueError("initial_cells must be a positive integer")
    if type(max_depth) is not int or not 0 <= max_depth <= 60:
        raise ValueError("max_depth must be an integer from zero through 60")
    if type(require_budget) is not bool:
        raise ValueError("require_budget must be a boolean")

    with ctx.workprec(precision_bits):
        compiled = _compile_row(row)
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
                raise VerificationError("a certified-positive run has negative integral")
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
            initial_left = fmpq(-2) + fmpq(4 * initial_index, initial_cells)
            initial_right = fmpq(-2) + fmpq(4 * (initial_index + 1), initial_cells)
            stack: list[tuple[fmpq, fmpq, int]] = [(initial_left, initial_right, 0)]
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
                    upper = enclosure.upper()
                    if upper > 0:
                        uncertain_integral += arb(right - left) * upper
                else:
                    midpoint = (left + right) / 2
                    next_depth = depth + 1
                    split_cells += 1
                    max_depth_seen = max(max_depth_seen, next_depth)
                    stack.append((midpoint, right, next_depth))
                    stack.append((left, midpoint, next_depth))

        flush_positive_run()
        total = positive_integral + uncertain_integral
        total_upper = _endpoint(total, upper=True)
        if require_budget and total_upper > 1:
            raise BudgetVerificationError(total_upper)

        support = _support_charge(row, compiled)
        support_upper = _endpoint(support, upper=True)
        quadratic_c0 = compiled.a0 + 2 * compiled.a2 / 3 - support - arb(_GUARD)
        result = RowVerification(
            atom_count=len(row.atoms),
            precision_bits=precision_bits,
            initial_cells=initial_cells,
            max_depth=max_depth,
            positive_antiderivative_upper=_endpoint(positive_integral, upper=True),
            uncertain_rectangle_upper=_endpoint(uncertain_integral, upper=True),
            total_positive_part_upper=total_upper,
            support_charge_upper=support_upper,
            quadratic_c0_lower=_endpoint(quadratic_c0, upper=False),
            quadratic_a1_lower=row.a1,
            quadratic_a2_lower=row.a2,
            audit=CellAudit(
                negative_cells=negative_cells,
                positive_cells=positive_cells,
                split_cells=split_cells,
                terminal_cells=terminal_cells,
                max_depth_seen=max_depth_seen,
            ),
        )
        if require_budget and not result.budget_pass:
            raise BudgetVerificationError(result.total_positive_part_upper)
        return result


def verify_station_row(
    bundle_path: Path,
    row_index: int,
    *,
    precision_bits: int = 192,
    initial_cells: int = 20,
    max_depth: int = 14,
) -> RowVerification:
    """Authenticate and rigorously verify one released Station row."""

    row = load_station_row(bundle_path, row_index)
    return verify_dual_row(
        row,
        precision_bits=precision_bits,
        initial_cells=initial_cells,
        max_depth=max_depth,
        require_budget=True,
    )


def row_quadratic(result: RowVerification, mean: fmpq) -> fmpq:
    """Evaluate a verified row's lower-bound quadratic exactly."""

    return (
        result.quadratic_c0_lower
        + result.quadratic_a1_lower * mean
        + result.quadratic_a2_lower * mean * mean / 2
    )


def certified_global_lower(
    rows: Sequence[RowVerification],
    intervals: Sequence[tuple[fmpq, fmpq]] = STATION_MEAN_INTERVALS,
) -> fmpq:
    """Aggregate concave row quadratics over an exact cover of ``[0, 1]``."""

    if len(rows) != len(intervals) or not rows:
        raise VerificationError("verified rows and mean intervals must have equal nonzero length")

    previous_right = fmpq(0)
    floors: list[fmpq] = []
    for index, (row, (left, right)) in enumerate(zip(rows, intervals, strict=True)):
        if left != previous_right or right <= left:
            raise VerificationError(f"mean intervals do not form an exact cover at row {index}")
        if row.quadratic_a2_lower >= 0:
            raise VerificationError(f"row {index} lower-bound quadratic is not concave")
        floors.append(min(row_quadratic(row, left), row_quadratic(row, right)))
        previous_right = right
    if previous_right != 1:
        raise VerificationError("mean intervals do not end at one")
    return min(floors)


def verify_station_rows(
    bundle_path: Path,
    row_indexes: Sequence[int] | None = None,
    *,
    precision_bits: int = 192,
) -> Mapping[int, RowVerification]:
    """Authenticate and verify selected Station rows with their released run depths."""

    indexes = tuple(range(len(STATION_ROW_RUNS))) if row_indexes is None else tuple(row_indexes)
    if not indexes or any(type(index) is not int or index not in range(4) for index in indexes):
        raise ValueError("row indexes must be integers from zero through three")
    if len(set(indexes)) != len(indexes):
        raise ValueError("row indexes must not contain duplicates")

    verified: dict[int, RowVerification] = {}
    for index in indexes:
        initial_cells, max_depth = STATION_ROW_RUNS[index]
        verified[index] = verify_station_row(
            bundle_path,
            index,
            precision_bits=precision_bits,
            initial_cells=initial_cells,
            max_depth=max_depth,
        )
    return verified


def verify_station_baseline(
    bundle_path: Path,
    *,
    precision_bits: int = 192,
) -> BaselineVerification:
    """Run and aggregate the complete four-row independent Arb replay."""

    verified = verify_station_rows(bundle_path, precision_bits=precision_bits)
    rows = tuple(verified[index] for index in range(4))
    global_lower = certified_global_lower(rows)
    margin = global_lower - STATION_RELEASED_CLAIM
    if margin <= 0:
        raise VerificationError("independent replay does not establish the released claim")
    return BaselineVerification(
        rows=rows,
        certified_global_lower=global_lower,
        margin_above_released_claim=margin,
    )


def row_verification_record(result: RowVerification) -> dict[str, object]:
    """Convert an Arb result to a stable JSON-compatible evidence record."""

    return {
        "atom_count": result.atom_count,
        "precision_bits": result.precision_bits,
        "initial_cells": result.initial_cells,
        "max_depth": result.max_depth,
        "positive_antiderivative_upper": str(result.positive_antiderivative_upper),
        "uncertain_rectangle_upper": str(result.uncertain_rectangle_upper),
        "total_positive_part_upper": str(result.total_positive_part_upper),
        "support_charge_upper": str(result.support_charge_upper),
        "quadratic_c0_lower": str(result.quadratic_c0_lower),
        "quadratic_a1_lower": str(result.quadratic_a1_lower),
        "quadratic_a2_lower": str(result.quadratic_a2_lower),
        "budget_pass": result.budget_pass,
        "audit": {
            "negative_cells": result.audit.negative_cells,
            "positive_cells": result.audit.positive_cells,
            "split_cells": result.audit.split_cells,
            "terminal_cells": result.audit.terminal_cells,
            "max_depth_seen": result.audit.max_depth_seen,
        },
    }
