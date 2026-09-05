from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path

from tools.build_arxiv_bundle import SOURCE_MAP, build_arxiv_bundle


def test_arxiv_bundle_is_allowlisted_and_deterministic(tmp_path: Path) -> None:
    first = build_arxiv_bundle(tmp_path / "first.tar.gz")
    second = build_arxiv_bundle(tmp_path / "second.tar.gz")

    assert first.read_bytes() == second.read_bytes()

    expected = {archive_name for _, archive_name in SOURCE_MAP}
    expected.add("MANIFEST.sha256")
    with tarfile.open(first, "r:gz") as archive:
        members = archive.getmembers()
        assert {member.name for member in members} == expected
        assert all(member.isfile() for member in members)
        assert all(member.mtime == 0 for member in members)


def test_arxiv_bundle_manifest_authenticates_every_source(tmp_path: Path) -> None:
    bundle = build_arxiv_bundle(tmp_path / "bundle.tar.gz")

    with tarfile.open(bundle, "r:gz") as archive:
        payloads = {
            member.name: archive.extractfile(member).read()
            for member in archive.getmembers()
            if member.name != "MANIFEST.sha256"
        }
        manifest = archive.extractfile("MANIFEST.sha256").read().decode("ascii")

    expected_manifest = "".join(
        f"{hashlib.sha256(payload).hexdigest()}  {name}\n"
        for name, payload in sorted(payloads.items())
    )
    assert manifest == expected_manifest
