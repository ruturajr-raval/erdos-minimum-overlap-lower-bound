"""Compile the standalone MPFI/C center verifier."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def _attempt(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, capture_output=True)


def _brew_prefix(package: str) -> Path:
    result = subprocess.run(
        ["brew", "--prefix", package],
        check=True,
        text=True,
        capture_output=True,
    )
    return Path(result.stdout.strip())


def compile_verifier(source: Path, output: Path) -> None:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise RuntimeError("a C compiler is required")

    common = [
        compiler,
        "-std=c11",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
    ]
    libraries = ["-lmpfi", "-lmpfr", "-lgmp", "-lm"]
    system_command = [*common, str(source), *libraries, "-o", str(output)]
    system_result = _attempt(system_command)
    if system_result.returncode == 0:
        print(" ".join(system_command))
        return

    if shutil.which("brew") is None:
        raise RuntimeError(f"MPFI compilation failed:\n{system_result.stderr}")

    prefixes = tuple(_brew_prefix(package) for package in ("mpfi", "mpfr", "gmp"))
    includes = [f"-I{prefix / 'include'}" for prefix in prefixes]
    links = [
        flag
        for prefix in prefixes
        for flag in (f"-L{prefix / 'lib'}", f"-Wl,-rpath,{prefix / 'lib'}")
    ]
    fallback_command = [
        *common,
        *includes,
        str(source),
        *links,
        *libraries,
        "-o",
        str(output),
    ]
    fallback_result = _attempt(fallback_command)
    if fallback_result.returncode != 0:
        raise RuntimeError(
            "MPFI compilation failed with system and Homebrew paths:\n"
            f"system:\n{system_result.stderr}\n"
            f"Homebrew:\n{fallback_result.stderr}"
        )
    print(" ".join(fallback_command))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).with_name("center_mpfi.c"),
    )
    parser.add_argument("--output", type=Path, default=Path("center_mpfi"))
    args = parser.parse_args()
    compile_verifier(args.source, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
