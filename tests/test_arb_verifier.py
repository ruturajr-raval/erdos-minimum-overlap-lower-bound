from __future__ import annotations

from pathlib import Path

import pytest
from flint import fmpq

from minoverlap.arb_verifier import (
    BudgetVerificationError,
    CellAudit,
    CertificateFormatError,
    RowVerification,
    VerificationError,
    certified_global_lower,
    load_station_row,
    parse_station_row,
    row_verification_record,
    verify_dual_row,
    verify_station_row,
)

ROOT = Path(__file__).parents[1]
BUNDLE = ROOT / "upstream" / "station" / "autocorr_6_5_certificate_data.npz"


def test_authenticated_parser_loads_exact_row_without_numpy() -> None:
    row = load_station_row(BUNDLE, 3)

    assert len(row.atoms) == 400
    assert row.a0 == fmpq(1_197_933_558_518_621, 2_000_000_000_000_000)
    assert row.a1 == fmpq(240_762_165_011_211, 1_250_000_000_000_000)
    assert row.a2 == fmpq(-6_661_158_969_129_829, 20_000_000_000_000_000)
    assert row.atoms[0].xi == fmpq(1, 4)
    assert row.atoms[-1].xi == fmpq(2551, 4)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ("1\t0\t-1\t1\n1\t1\t0", "end"),
        ("1 0 -1 1\n1\t1\t0\n", "header"),
        ("1\t0\t-1\t2\n1\t1\t0\n", "declares"),
        ("nan\t0\t-1\t1\n1\t1\t0\n", "decimal"),
        ("1\t0\t-1\t1\n1\t0\t0\n", "positive"),
        ("1\t0\t-1\t1\n1\t1\t0\n\n", "empty"),
    ],
)
def test_parser_rejects_noncanonical_or_invalid_rows(payload: str, match: str) -> None:
    with pytest.raises(CertificateFormatError, match=match):
        parse_station_row(payload)


def test_parser_preserves_scientific_decimals_as_exact_rationals() -> None:
    row = parse_station_row("1.25e-1\t-2.5E+1\t0\t1\n2.5e-1\t1e-7\t-3e-4\n")

    assert row.a0 == fmpq(1, 8)
    assert row.a1 == -25
    assert row.atoms[0].xi == fmpq(1, 4)
    assert row.atoms[0].alpha == fmpq(1, 10_000_000)
    assert row.atoms[0].beta == fmpq(-3, 10_000)


def test_fast_station_row_passes_independent_arb_replay() -> None:
    result = verify_station_row(
        BUNDLE,
        3,
        precision_bits=192,
        initial_cells=20,
        max_depth=14,
    )

    assert result.atom_count == 400
    assert result.budget_pass
    assert fmpq(999, 1000) < result.total_positive_part_upper < 1
    assert result.quadratic_c0_lower > fmpq(369_791_719, 1_000_000_000)
    assert result.quadratic_a1_lower > 0
    assert result.quadratic_a2_lower < 0
    assert result.audit.positive_cells > 0
    assert result.audit.negative_cells > 0


def test_budget_mutation_fails_closed() -> None:
    row = parse_station_row("2\t0\t0\t1\n1\t1e-3\t0\n")

    with pytest.raises(BudgetVerificationError) as raised:
        verify_dual_row(
            row,
            precision_bits=128,
            initial_cells=4,
            max_depth=2,
        )

    assert raised.value.upper > 1


def test_authenticated_loader_rejects_modified_bundle(tmp_path: Path) -> None:
    mutated = bytearray(BUNDLE.read_bytes())
    mutated[-1] ^= 1
    path = tmp_path / "mutated.npz"
    path.write_bytes(mutated)

    with pytest.raises(CertificateFormatError, match="hash mismatch"):
        load_station_row(path, 3)


def synthetic_result(c0: fmpq, a1: fmpq, a2: fmpq) -> RowVerification:
    return RowVerification(
        atom_count=1,
        precision_bits=192,
        initial_cells=1,
        max_depth=0,
        positive_antiderivative_upper=fmpq(0),
        uncertain_rectangle_upper=fmpq(0),
        total_positive_part_upper=fmpq(1),
        support_charge_upper=fmpq(0),
        quadratic_c0_lower=c0,
        quadratic_a1_lower=a1,
        quadratic_a2_lower=a2,
        audit=CellAudit(0, 1, 0, 0, 0),
    )


def test_global_aggregation_uses_exact_concave_endpoint_floors() -> None:
    rows = (
        synthetic_result(fmpq(2, 5), fmpq(0), fmpq(-1, 100)),
        synthetic_result(fmpq(2, 5), fmpq(0), fmpq(-1, 100)),
    )
    intervals = ((fmpq(0), fmpq(1, 2)), (fmpq(1, 2), fmpq(1)))

    assert certified_global_lower(rows, intervals) == fmpq(79, 200)


def test_global_aggregation_rejects_gap_and_nonconcave_row() -> None:
    concave = synthetic_result(fmpq(2, 5), fmpq(0), fmpq(-1, 100))
    nonconcave = synthetic_result(fmpq(2, 5), fmpq(0), fmpq(0))

    with pytest.raises(VerificationError, match="cover"):
        certified_global_lower(
            (concave, concave),
            ((fmpq(0), fmpq(2, 5)), (fmpq(1, 2), fmpq(1))),
        )
    with pytest.raises(VerificationError, match="concave"):
        certified_global_lower((nonconcave,), ((fmpq(0), fmpq(1)),))


def test_row_record_is_json_compatible() -> None:
    record = row_verification_record(
        synthetic_result(fmpq(2, 5), fmpq(1, 10), fmpq(-1, 100))
    )

    assert record["budget_pass"] is True
    assert record["quadratic_c0_lower"] == "2/5"
    assert record["audit"] == {
        "negative_cells": 0,
        "positive_cells": 1,
        "split_cells": 0,
        "terminal_cells": 0,
        "max_depth_seen": 0,
    }
