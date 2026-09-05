from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from minoverlap.release_audit import audit_project_release

ROOT = Path(__file__).parents[1]


def copy_release_subset(destination: Path) -> Path:
    relative_paths = [
        "certificates/center-038055925.tsv",
        "evidence/center-038055925-verification.json",
        "evidence/noncentral-038055925-replay.json",
        "evidence/noncentral-038055925-report.csv",
        "evidence/noncentral-038055925-report.json",
        "evidence/noncentral-038055925-report.log",
        "evidence.json",
        "src/minoverlap/center_certificate.py",
        "verification/center_mpfi.c",
    ]
    for relative in relative_paths:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return destination


def test_project_release_audit_authenticates_complete_evidence() -> None:
    result = audit_project_release(ROOT)

    assert result["status"] == "pass"
    assert result["target"] == "0.38055925"
    assert result["mean_bins_covered"] == 172
    assert result["noncentral_bins"] == 170


def test_project_release_audit_rejects_certificate_mutation(tmp_path: Path) -> None:
    root = copy_release_subset(tmp_path)
    certificate = root / "certificates/center-038055925.tsv"
    certificate.write_bytes(certificate.read_bytes().replace(b"5.94", b"5.95", 1))

    with pytest.raises(ValueError, match="hash mismatch"):
        audit_project_release(root)


def test_project_release_audit_rejects_coverage_mutation(tmp_path: Path) -> None:
    root = copy_release_subset(tmp_path)
    path = root / "evidence/noncentral-038055925-replay.json"
    evidence = json.loads(path.read_text())
    evidence["coverage"]["checked_bins"] = 169
    path.write_text(json.dumps(evidence))

    with pytest.raises(ValueError, match="170 bins"):
        audit_project_release(root)


def test_project_release_audit_rejects_noncentral_report_mutation(
    tmp_path: Path,
) -> None:
    root = copy_release_subset(tmp_path)
    path = root / "evidence/noncentral-038055925-report.csv"
    path.write_bytes(path.read_bytes().replace(b",True,", b",False,", 1))

    with pytest.raises(ValueError, match="hash mismatch"):
        audit_project_release(root)
