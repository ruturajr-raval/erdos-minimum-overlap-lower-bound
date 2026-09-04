from __future__ import annotations

import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from minoverlap.baseline import BASELINE_LOWER, DATA_SHA256, VERIFIER_SHA256, artifact_sha256

ROOT = Path(__file__).parents[1]


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text())


def test_evidence_manifest_authenticates_vendored_station_inputs() -> None:
    evidence = load_json("evidence.json")
    sources = evidence["sources"]
    assert isinstance(sources, dict)
    station = sources["station_v2"]
    assert isinstance(station, dict)
    artifacts = station["artifacts"]
    assert isinstance(artifacts, dict)

    assert artifacts["autocorr_6_5_certificate_data.npz"] == DATA_SHA256
    assert artifacts["mpfi_positive_budget.c"] == VERIFIER_SHA256
    assert artifact_sha256(
        ROOT / "upstream/station/autocorr_6_5_certificate_data.npz"
    ) == artifacts["autocorr_6_5_certificate_data.npz"]
    assert artifact_sha256(
        ROOT / "upstream/station/mpfi_positive_budget.c"
    ) == artifacts["mpfi_positive_budget.c"]


def test_witness_generation_manifest_authenticates_retained_subset() -> None:
    bundle = ROOT / "upstream/station/witness_generation"
    manifest = json.loads((bundle / "file_manifest.json").read_text())

    assert isinstance(manifest, dict)
    assert manifest["modified_by"] == "Ruturaj R Raval"
    assert manifest["modification_year"] == 2026
    files = manifest["files"]
    assert isinstance(files, list)
    paths = [entry["path"] for entry in files]
    assert len(paths) == len(set(paths))
    assert "README.md" not in paths

    for entry in files:
        path = bundle / entry["path"]
        assert path.is_file()
        assert path.stat().st_size == entry["bytes"]
        assert artifact_sha256(path) == entry["sha256"]


def test_station_replay_exceeds_only_the_released_station_target() -> None:
    replay = load_json("evidence/station-replay.json")
    certified = Decimal(str(replay["certified_global_lower_decimal"]))

    assert replay["all_rows_passed"] is True
    assert Fraction(certified) >= BASELINE_LOWER
    assert certified > Decimal("0.380552")
    assert certified < Decimal("0.38055470")


def test_separate_arb_replay_independently_matches_station_claim() -> None:
    replay = load_json("evidence/station-arb-replay.json")
    certified = Decimal(str(replay["certified_global_lower_decimal"]))

    assert replay["all_rows_passed"] is True
    assert certified > Decimal("0.380552")
    assert certified < Decimal("0.38055470")
    boundary = replay["independence_boundary"]
    assert isinstance(boundary, dict)
    assert "Arb arithmetic backend" in boundary["independent"]
    assert "dual row formula" in boundary["shared"]


def test_prior_art_is_separated_from_the_project_claim() -> None:
    evidence = load_json("evidence.json")
    prior_art = load_json("evidence/prior-art-replay.json")

    claims = evidence["project_novel_claims"]
    assert isinstance(claims, list)
    assert len(claims) == 1
    assert claims[0]["claim"] == "c_E > 0.38055925"
    assert prior_art["source_material_vendored"] is False
    assert prior_art["declared_license"] is None
    assert prior_art["repository_reported_target"] == "0.38055470"
    coverage = prior_art["coverage"]
    assert isinstance(coverage, dict)
    assert coverage["all_bins_exactly_once"] is True
    assert coverage["all_bins_passed"] is True


def test_noncentral_replay_covers_every_unreplaced_mean_bin() -> None:
    replay = load_json("evidence/noncentral-038055925-replay.json")

    assert replay["target"] == "0.38055925"
    assert replay["source_material_vendored"] is False
    coverage = replay["coverage"]
    assert isinstance(coverage, dict)
    assert coverage["total_mean_bins"] == 172
    assert coverage["checked_bins"] == 170
    assert coverage["replaced_center_bins"] == [85, 86]
    assert coverage["all_checked_bins_passed"] is True


def test_project_center_certificate_has_two_independent_verification_paths() -> None:
    evidence = load_json("evidence/center-038055925-verification.json")

    assert evidence["target"] == "0.38055925"
    certificate = evidence["certificate"]
    assert isinstance(certificate, dict)
    assert artifact_sha256(ROOT / certificate["path"]) == certificate["sha256"]

    python_arb = evidence["python_arb"]
    mpfi_c = evidence["mpfi_c"]
    assert isinstance(python_arb, dict)
    assert isinstance(mpfi_c, dict)
    assert artifact_sha256(ROOT / python_arb["implementation"]) == (
        python_arb["implementation_sha256"]
    )
    assert artifact_sha256(ROOT / mpfi_c["implementation"]) == (
        mpfi_c["implementation_sha256"]
    )
    assert Decimal(python_arb["denominator_margin"]) > 0
    assert Decimal(mpfi_c["denominator_margin_lower"]) > 0
