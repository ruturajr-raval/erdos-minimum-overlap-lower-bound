from __future__ import annotations

from pathlib import Path

import pytest

from tools.build_release_assets import (
    CHECKSUMS_NAME,
    PDF_NAME,
    SOURCE_NAME,
    VERSION,
    build_release_assets,
    verify_release_assets,
)

FAKE_PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


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

    build_release_assets(pdf, output)
    first = _snapshot(output)
    build_release_assets(pdf, output)
    second = _snapshot(output)

    assert first == second
    assert set(first) == {PDF_NAME, SOURCE_NAME, CHECKSUMS_NAME}
    assert verify_release_assets(output) == {
        line.split("  ", maxsplit=1)[1]: line.split("  ", maxsplit=1)[0]
        for line in first[CHECKSUMS_NAME].decode("ascii").splitlines()
    }


def test_release_asset_verification_rejects_tampering(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(FAKE_PDF)
    output = tmp_path / "release"
    build_release_assets(pdf, output)

    with (output / PDF_NAME).open("ab") as target:
        target.write(b"tampered")

    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_release_assets(output)


def test_release_asset_verification_rejects_unexpected_file(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(FAKE_PDF)
    output = tmp_path / "release"
    build_release_assets(pdf, output)
    (output / "unexpected.txt").write_text("unexpected\n", encoding="ascii")

    with pytest.raises(ValueError, match="exact expected set"):
        verify_release_assets(output)


def test_release_asset_verification_rejects_reordered_checksums(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(FAKE_PDF)
    output = tmp_path / "release"
    build_release_assets(pdf, output)
    manifest = output / CHECKSUMS_NAME
    lines = manifest.read_text(encoding="ascii").splitlines()
    manifest.write_text("\n".join(reversed(lines)) + "\n", encoding="ascii")

    with pytest.raises(ValueError, match="not canonical"):
        verify_release_assets(output)


def test_release_metadata_matches_archival_assets() -> None:
    metadata = (Path(__file__).parents[1] / "release.yaml").read_text(
        encoding="ascii"
    )

    assert f"version: {VERSION}" in metadata
    assert "tag: v0.3.1" in metadata
    assert "version_doi: 10.5281/zenodo.22647743" in metadata
    assert "concept_doi: 10.5281/zenodo.22260847" in metadata
    assert f"name: {PDF_NAME}" in metadata
    assert f"name: {SOURCE_NAME}" in metadata
    assert "size_bytes: 91673" in metadata
    assert "size_bytes: 47883" in metadata
    assert "name: SHA256SUMS" in metadata
    assert "size_bytes: 244" in metadata
    assert (
        "sha256: "
        "e3a4dad76eb50244f07425e7c75fad43f155db5244cc2ee2eb49fed8ba69574f"
        in metadata
    )
    assert (
        "sha256: "
        "03753cd986592973bd739c546a9a463ca1eed1aec9fc0058475462751ff1a18b"
        in metadata
    )
    assert (
        "sha256: "
        "46945e89783298a43196735b4e3ca0b502841aba55be3cc5998c6598589be92b"
        in metadata
    )
