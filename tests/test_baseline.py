from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from minoverlap.baseline import (
    BASELINE_LOWER,
    MEAN_INTERVALS,
    ROW_SHA256,
    artifact_sha256,
    certified_global_lower,
    compile_mpfi_verifier,
    extract_rows,
    parse_verifier_output,
    run_mpfi_row,
    validate_mean_intervals,
    validate_row_text,
)

ROOT = Path(__file__).parents[1]
UPSTREAM = ROOT / "upstream" / "station"


def test_vendored_artifact_hashes_match_release() -> None:
    assert artifact_sha256(UPSTREAM / "autocorr_6_5_certificate_data.npz") == (
        "c9fdb2881874c4797acca21be2ab4fcf7b7a43e75ed763ce1f17d17e269e7453"
    )
    assert artifact_sha256(UPSTREAM / "mpfi_positive_budget.c") == (
        "a967d8dfd18456a80c79984c69eb28b88a7548bf001c505455f97808a704274d"
    )


def test_extract_rows_authenticates_each_payload(tmp_path: Path) -> None:
    paths = extract_rows(
        UPSTREAM / "autocorr_6_5_certificate_data.npz",
        tmp_path,
    )
    assert [artifact_sha256(path) for path in paths] == list(ROW_SHA256)


def test_validate_mean_intervals_covers_unit_interval() -> None:
    validate_mean_intervals(MEAN_INTERVALS)


def test_validate_mean_intervals_rejects_gap() -> None:
    with pytest.raises(ValueError, match="gap"):
        validate_mean_intervals(
            (
                (Fraction(0), Fraction("0.2")),
                (Fraction("0.3"), Fraction(1)),
            )
        )


def test_validate_row_rejects_nonpositive_alpha() -> None:
    with pytest.raises(ValueError, match="alpha"):
        validate_row_text("1 0 -1 1\n0.5 0 -0.1\n")


def test_parse_verifier_output_requires_success() -> None:
    with pytest.raises(ValueError, match="budget"):
        parse_verifier_output(
            "\n".join(
                [
                    "total_positive_part_upper=1",
                    "support_charge_upper=0",
                    "quadratic_c0_lower=0",
                    "quadratic_a1_lower=0",
                    "quadratic_a2_lower=-1",
                    "budget_pass=false",
                ]
            )
        )


@pytest.mark.parametrize(
    "total",
    ["nan", "inf", "-1", "1.0000000000000000001"],
)
def test_parse_verifier_output_rejects_invalid_success_budget(total: str) -> None:
    with pytest.raises(ValueError, match="total_positive_part_upper"):
        parse_verifier_output(
            "\n".join(
                [
                    f"total_positive_part_upper={total}",
                    "support_charge_upper=0",
                    "quadratic_c0_lower=0",
                    "quadratic_a1_lower=0",
                    "quadratic_a2_lower=-1",
                    "budget_pass=true",
                ]
            )
        )


def test_run_mpfi_row_validates_input_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invalid_row = tmp_path / "invalid.tsv"
    invalid_row.write_text("nan\t0\t-1\t1\n1\t1\t0\n")

    def unexpected_run(*_: object, **__: object) -> None:
        pytest.fail("invalid input reached the C verifier")

    monkeypatch.setattr("minoverlap.baseline.subprocess.run", unexpected_run)

    with pytest.raises(ValueError, match="non-finite"):
        run_mpfi_row(tmp_path / "verifier", invalid_row, 1, 1)


def test_certified_global_lower_matches_released_certificate() -> None:
    rows = (
        {
            "quadratic_c0_lower": "0.380552257389830222107376462494",
            "quadratic_a1_lower": "0",
            "quadratic_a2_lower": "-0.000000000000000000000000000001",
        },
        {
            "quadratic_c0_lower": "0.381",
            "quadratic_a1_lower": "0",
            "quadratic_a2_lower": "-0.0001",
        },
        {
            "quadratic_c0_lower": "0.381",
            "quadratic_a1_lower": "0",
            "quadratic_a2_lower": "-0.0001",
        },
        {
            "quadratic_c0_lower": "0.381",
            "quadratic_a1_lower": "0",
            "quadratic_a2_lower": "-0.0001",
        },
    )
    assert certified_global_lower(rows, MEAN_INTERVALS) <= BASELINE_LOWER


def test_compile_verifier_prefers_system_toolchain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    class Completed:
        returncode = 0
        stderr = ""

    def fake_run(command: list[str], **_: object) -> Completed:
        commands.append(command)
        return Completed()

    monkeypatch.setattr("minoverlap.baseline.subprocess.run", fake_run)
    monkeypatch.setattr("minoverlap.baseline.shutil.which", lambda _: "/usr/bin/cc")
    monkeypatch.setattr(
        "minoverlap.baseline._dependency_prefix",
        lambda _: pytest.fail("Homebrew lookup should not run after a successful system compile"),
    )

    source = tmp_path / "verifier.c"
    source.write_text("int main(void) { return 0; }\n")
    output = compile_mpfi_verifier(source, tmp_path / "verifier")

    assert output == tmp_path / "verifier"
    assert commands == [
        [
            "/usr/bin/cc",
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
    ]
