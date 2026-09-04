from __future__ import annotations

from pathlib import Path

import pytest
from flint import fmpq

from minoverlap.center_certificate import (
    CenterCertificateError,
    CenterVerificationError,
    parse_center_certificate,
    verify_center_certificate,
)

ROOT = Path(__file__).parents[1]
RELEASED_CERTIFICATE = ROOT / "certificates" / "center-038055925.tsv"


def synthetic_certificate(target: str = "0.2") -> str:
    return "\n".join(
        [
            "minimum-overlap-center-certificate-v1",
            f"target\t{target}",
            "mean_abs_max\t0.003125",
            "second_moment_multiplier\t0.000001",
            "parseval_order\t1",
            "parseval_multiplier\t0.000001",
            "cosine_count\t1",
            "cosine\t1\t0.000001",
            "",
        ]
    )


def test_parser_preserves_exact_decimal_semantics() -> None:
    certificate = parse_center_certificate(synthetic_certificate())

    assert certificate.target == fmpq(1, 5)
    assert certificate.mean_abs_max == fmpq(1, 320)
    assert certificate.second_moment_multiplier == fmpq(1, 1_000_000)
    assert certificate.parseval_order == 1
    assert certificate.cosine_rows[0].frequency == 1


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda text: text.replace("\n", "\r\n"), "canonical"),
        (lambda text: text.rstrip("\n"), "canonical"),
        (lambda text: text.replace("cosine_count\t1", "cosine_count\t2"), "declares"),
        (
            lambda text: text.replace(
                "cosine\t1\t0.000001",
                "cosine\t1\t0.000001\ncosine\t0.5\t0.000001",
            ).replace("cosine_count\t1", "cosine_count\t2"),
            "strictly increasing",
        ),
        (
            lambda text: text.replace(
                "second_moment_multiplier\t0.000001",
                "second_moment_multiplier\t0",
            ),
            "positive",
        ),
    ],
)
def test_parser_rejects_noncanonical_or_invalid_certificates(
    mutation: object,
    match: str,
) -> None:
    assert callable(mutation)
    with pytest.raises(CenterCertificateError, match=match):
        parse_center_certificate(mutation(synthetic_certificate()))


def test_arb_verifier_certifies_a_simple_positive_certificate(tmp_path: Path) -> None:
    path = tmp_path / "center.tsv"
    path.write_text(synthetic_certificate())

    result = verify_center_certificate(
        path,
        precision_bits=128,
        initial_cells=16,
        max_depth=2,
    )

    assert result.certified
    assert result.target == fmpq(1, 5)
    assert result.denominator_upper < result.target_denominator
    assert result.audit.positive_cells > 0


def test_arb_verifier_fails_closed_when_target_is_too_large(tmp_path: Path) -> None:
    path = tmp_path / "center.tsv"
    path.write_text(synthetic_certificate("0.3"))

    with pytest.raises(CenterVerificationError, match="does not establish"):
        verify_center_certificate(
            path,
            precision_bits=128,
            initial_cells=16,
            max_depth=2,
        )


def test_released_center_certificate_passes_arb_verification() -> None:
    result = verify_center_certificate(
        RELEASED_CERTIFICATE,
        precision_bits=256,
        initial_cells=4_096,
        max_depth=16,
    )

    assert result.certificate_sha256 == (
        "b02a45a645337c74215a365e82f403990eeb9413e3f8771e719e5e5397da39e8"
    )
    assert result.target == fmpq(1_522_237, 4_000_000)
    assert result.denominator_upper < result.target_denominator
    assert result.denominator_margin > fmpq(1, 2_000_000)
