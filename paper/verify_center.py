"""Run the standalone Python-Arb center-certificate verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from center_certificate import center_verification_record, verify_center_certificate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--precision", type=int, default=256)
    parser.add_argument("--initial-cells", type=int, default=4096)
    parser.add_argument("--max-depth", type=int, default=16)
    args = parser.parse_args()

    result = verify_center_certificate(
        args.certificate,
        precision_bits=args.precision,
        initial_cells=args.initial_cells,
        max_depth=args.max_depth,
    )
    print(json.dumps(center_verification_record(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
