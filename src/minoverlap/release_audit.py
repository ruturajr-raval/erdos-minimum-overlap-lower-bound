"""Static integrity audit for the certified project release."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from minoverlap.baseline import artifact_sha256, project_root
from minoverlap.center_certificate import load_center_certificate

_TARGET = "0.38055925"
_CERTIFICATE = Path("certificates/center-038055925.tsv")
_CENTER_EVIDENCE = Path("evidence/center-038055925-verification.json")
_NONCENTRAL_EVIDENCE = Path("evidence/noncentral-038055925-replay.json")
_MAIN_EVIDENCE = Path("evidence.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load release evidence: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"release evidence is not an object: {path}")
    return value


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"release evidence field is not an object: {field}")
    return value


def _check_hash(root: Path, relative: object, expected: object, field: str) -> str:
    if not isinstance(relative, str) or not isinstance(expected, str):
        raise ValueError(f"invalid path or hash in release evidence: {field}")
    path = root / relative
    if not path.is_file():
        raise ValueError(f"release artifact is missing: {relative}")
    observed = artifact_sha256(path)
    if observed != expected:
        raise ValueError(f"release artifact hash mismatch for {relative}: {observed}")
    return observed


def audit_project_release(root: Path | None = None) -> dict[str, object]:
    """Authenticate the project certificate, verifier sources, and evidence."""

    root = root or project_root()
    center = _load_json(root / _CENTER_EVIDENCE)
    noncentral = _load_json(root / _NONCENTRAL_EVIDENCE)
    main = _load_json(root / _MAIN_EVIDENCE)

    if center.get("schema") != "minimum-overlap-center-verification-v1":
        raise ValueError("unexpected center evidence schema")
    if noncentral.get("schema") != "minimum-overlap-noncentral-replay-v1":
        raise ValueError("unexpected noncentral evidence schema")
    if center.get("target") != _TARGET or noncentral.get("target") != _TARGET:
        raise ValueError("release evidence target mismatch")

    certificate_record = _mapping(center.get("certificate"), "certificate")
    if certificate_record.get("path") != str(_CERTIFICATE):
        raise ValueError("center evidence points to an unexpected certificate")
    certificate_hash = _check_hash(
        root,
        certificate_record.get("path"),
        certificate_record.get("sha256"),
        "certificate",
    )
    certificate, parsed_hash = load_center_certificate(root / _CERTIFICATE)
    if parsed_hash != certificate_hash or str(certificate.target) != "1522237/4000000":
        raise ValueError("parsed center certificate identity mismatch")

    python_arb = _mapping(center.get("python_arb"), "python_arb")
    mpfi_c = _mapping(center.get("mpfi_c"), "mpfi_c")
    python_hash = _check_hash(
        root,
        python_arb.get("implementation"),
        python_arb.get("implementation_sha256"),
        "python_arb implementation",
    )
    c_hash = _check_hash(
        root,
        mpfi_c.get("implementation"),
        mpfi_c.get("implementation_sha256"),
        "mpfi_c implementation",
    )

    coverage = _mapping(noncentral.get("coverage"), "noncentral coverage")
    if (
        coverage.get("total_mean_bins") != 172
        or coverage.get("checked_bins") != 170
        or coverage.get("replaced_center_bins") != [85, 86]
        or coverage.get("all_checked_bins_passed") is not True
    ):
        raise ValueError("noncentral evidence does not cover the required 170 bins")

    claims = main.get("project_novel_claims")
    if not isinstance(claims, list) or len(claims) != 1:
        raise ValueError("main evidence must contain exactly one project claim")
    claim = _mapping(claims[0], "project claim")
    if (
        claim.get("claim") != "c_E > 0.38055925"
        or claim.get("certificate") != str(_CERTIFICATE)
        or claim.get("certificate_sha256") != certificate_hash
    ):
        raise ValueError("main evidence project claim does not match the certificate")

    return {
        "status": "pass",
        "target": _TARGET,
        "certificate_sha256": certificate_hash,
        "python_arb_sha256": python_hash,
        "mpfi_c_sha256": c_hash,
        "center_verifiers": 2,
        "noncentral_bins": 170,
        "mean_bins_covered": 172,
    }
