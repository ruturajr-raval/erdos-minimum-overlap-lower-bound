from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tools.build_release_assets import (
    CHECKSUMS_NAME,
    PDF_NAME,
    RELEASE_METADATA,
    SOURCE_NAME,
    VERSION,
    build_release_assets,
    verify_release_assets,
)

FAKE_PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def test_release_assets_are_exact_and_deterministic(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(FAKE_PDF)
    output = tmp_path / "release"

    build_release_assets(pdf, output, metadata_path=None)
    first = _snapshot(output)
    build_release_assets(pdf, output, metadata_path=None)
    second = _snapshot(output)

    assert first == second
    assert set(first) == {PDF_NAME, SOURCE_NAME, CHECKSUMS_NAME}
    assert verify_release_assets(output, metadata_path=None) == {
        line.split("  ", maxsplit=1)[1]: line.split("  ", maxsplit=1)[0]
        for line in first[CHECKSUMS_NAME].decode("ascii").splitlines()
    }


def test_release_asset_verification_rejects_tampering(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(FAKE_PDF)
    output = tmp_path / "release"
    build_release_assets(pdf, output, metadata_path=None)

    with (output / PDF_NAME).open("ab") as target:
        target.write(b"tampered")

    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_release_assets(output, metadata_path=None)


def test_release_asset_verification_rejects_unexpected_file(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(FAKE_PDF)
    output = tmp_path / "release"
    build_release_assets(pdf, output, metadata_path=None)
    (output / "unexpected.txt").write_text("unexpected\n", encoding="ascii")

    with pytest.raises(ValueError, match="exact expected set"):
        verify_release_assets(output, metadata_path=None)


def test_release_asset_verification_rejects_reordered_checksums(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(FAKE_PDF)
    output = tmp_path / "release"
    build_release_assets(pdf, output, metadata_path=None)
    manifest = output / CHECKSUMS_NAME
    lines = manifest.read_text(encoding="ascii").splitlines()
    manifest.write_text("\n".join(reversed(lines)) + "\n", encoding="ascii")

    with pytest.raises(ValueError, match="not canonical"):
        verify_release_assets(output, metadata_path=None)


def test_release_metadata_matches_archival_assets() -> None:
    metadata = RELEASE_METADATA.read_text(encoding="ascii")

    assert VERSION == "0.3.1"
    assert "tag: v0.3.1" in metadata
    assert "version_doi: 10.5281/zenodo.22647743" in metadata
    assert "concept_doi: 10.5281/zenodo.22260847" in metadata
    assert f"name: {PDF_NAME}" in metadata
    assert "size_bytes: 91673" in metadata
    assert (
        "sha256: "
        "e3a4dad76eb50244f07425e7c75fad43f155db5244cc2ee2eb49fed8ba69574f"
        in metadata
    )
    assert f"name: {SOURCE_NAME}" in metadata
    assert "size_bytes: 47883" in metadata
    assert (
        "sha256: "
        "03753cd986592973bd739c546a9a463ca1eed1aec9fc0058475462751ff1a18b"
        in metadata
    )
    assert f"name: {CHECKSUMS_NAME}" in metadata
    assert "size_bytes: 244" in metadata
    assert (
        "sha256: "
        "46945e89783298a43196735b4e3ca0b502841aba55be3cc5998c6598589be92b"
        in metadata
    )


def test_release_asset_verification_rejects_metadata_hash_mismatch(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(FAKE_PDF)
    output = tmp_path / "release"
    build_release_assets(pdf, output, metadata_path=None)

    release_pdf = output / PDF_NAME
    source = output / SOURCE_NAME
    checksums = output / CHECKSUMS_NAME
    metadata = tmp_path / "release.yaml"
    metadata.write_text(
        f"""version: {VERSION}
archive:
  release_assets:
    pdf:
      name: {PDF_NAME}
      size_bytes: {release_pdf.stat().st_size}
      sha256: {_sha256(release_pdf)}
    paper_source:
      name: {SOURCE_NAME}
      size_bytes: {source.stat().st_size}
      sha256: {_sha256(source)}
    checksums:
      name: {CHECKSUMS_NAME}
      size_bytes: {checksums.stat().st_size}
      sha256: {_sha256(checksums)}
""",
        encoding="ascii",
    )
    assert verify_release_assets(output, metadata)

    metadata.write_text(
        metadata.read_text(encoding="ascii").replace(
            _sha256(release_pdf),
            "0" * 64,
            1,
        ),
        encoding="ascii",
    )
    with pytest.raises(ValueError, match="metadata hash mismatch"):
        verify_release_assets(output, metadata)
