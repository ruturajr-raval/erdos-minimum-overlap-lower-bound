"""Build the deterministic, allowlisted arXiv source bundle."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import tarfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "dist/arxiv/erdos-minimum-overlap-038055925.tar.gz"

SOURCE_MAP = (
    ("paper/main.tex", "main.tex"),
    ("paper/ARXIV_README.txt", "README.txt"),
    ("LICENSE", "LICENSE"),
    ("NOTICE", "NOTICE"),
    ("THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
    (
        "certificates/center-038055925.tsv",
        "anc/certificates/center-038055925.tsv",
    ),
    (
        "src/minoverlap/center_certificate.py",
        "anc/python/center_certificate.py",
    ),
    ("paper/verify_center.py", "anc/python/verify_center.py"),
    ("paper/requirements-arxiv.txt", "anc/python/requirements.txt"),
    ("verification/center_mpfi.c", "anc/c/center_mpfi.c"),
    ("paper/build_center_mpfi.py", "anc/c/build_center_mpfi.py"),
    (
        "evidence/center-038055925-verification.json",
        "anc/evidence/center-038055925-verification.json",
    ),
    (
        "evidence/noncentral-038055925-replay.json",
        "anc/evidence/noncentral-038055925-replay.json",
    ),
    (
        "evidence/noncentral-038055925-report.csv",
        "anc/evidence/noncentral-038055925-report.csv",
    ),
    (
        "evidence/noncentral-038055925-report.json",
        "anc/evidence/noncentral-038055925-report.json",
    ),
    (
        "evidence/noncentral-038055925-report.log",
        "anc/evidence/noncentral-038055925-report.log",
    ),
)

FORBIDDEN_PAYLOADS = (
    b"/" + b"Users/",
    b"file" + b"://",
    bytes.fromhex("e28094"),
)


def _load_entries(root: Path) -> dict[str, bytes]:
    entries: dict[str, bytes] = {}
    for source_name, archive_name in SOURCE_MAP:
        source = root / source_name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"arXiv source is missing or not a regular file: {source_name}")
        payload = source.read_bytes()
        for forbidden in FORBIDDEN_PAYLOADS:
            if forbidden in payload:
                raise ValueError(
                    f"arXiv source contains a forbidden publication payload: {source_name}"
                )
        entries[archive_name] = payload
    return entries


def _manifest(entries: dict[str, bytes]) -> bytes:
    lines = [
        f"{hashlib.sha256(payload).hexdigest()}  {name}"
        for name, payload in sorted(entries.items())
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def _add_bytes(archive: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    archive.addfile(info, io.BytesIO(payload))


def build_arxiv_bundle(output: Path = DEFAULT_OUTPUT, root: Path = PROJECT_ROOT) -> Path:
    """Create a deterministic tar.gz containing only publication-approved files."""

    entries = _load_entries(root)
    entries["MANIFEST.sha256"] = _manifest(entries)
    output.parent.mkdir(parents=True, exist_ok=True)

    with (
        output.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed,
        tarfile.open(
            fileobj=compressed,
            mode="w",
            format=tarfile.USTAR_FORMAT,
        ) as archive,
    ):
        for name, payload in sorted(entries.items()):
            _add_bytes(archive, name, payload)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = build_arxiv_bundle(args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
