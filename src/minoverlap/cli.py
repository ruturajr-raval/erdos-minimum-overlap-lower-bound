from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from minoverlap.arb_verifier import (
    STATION_BUNDLE_SHA256,
    row_verification_record,
    verify_station_rows,
)
from minoverlap.arb_verifier import (
    certified_global_lower as certified_arb_global_lower,
)
from minoverlap.baseline import audit_baseline, verify_baseline
from minoverlap.baseline import project_root as baseline_project_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="minoverlap",
        description="Certificate tooling for the Erdos minimum-overlap campaign.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit", help="authenticate and structurally validate upstream artifacts")

    verify = subparsers.add_parser(
        "verify-baseline",
        help="run the released directed-arithmetic certificate verifier",
    )
    verify.add_argument(
        "--row",
        action="append",
        type=int,
        dest="rows",
        help="verify only this zero-based row; repeat to select multiple rows",
    )

    independent = subparsers.add_parser(
        "verify-independent",
        help="run the separate Python-Arb verifier against the released certificate",
    )
    independent.add_argument(
        "--row",
        action="append",
        type=int,
        dest="rows",
        help="verify only this zero-based row; repeat to select multiple rows",
    )
    independent.add_argument(
        "--precision",
        type=int,
        default=192,
        help="Arb working precision in bits (default: 192)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "audit":
        result = audit_baseline()
    elif args.command == "verify-baseline":
        result = verify_baseline(selected_rows=args.rows)
    elif args.command == "verify-independent":
        bundle = (
            baseline_project_root()
            / "upstream"
            / "station"
            / "autocorr_6_5_certificate_data.npz"
        )
        verified = verify_station_rows(
            bundle,
            row_indexes=args.rows,
            precision_bits=args.precision,
        )
        result = {
            "status": "pass",
            "backend": "python-flint Arb",
            "bundle_sha256": STATION_BUNDLE_SHA256,
            "verified_rows": {
                str(index): row_verification_record(row) for index, row in verified.items()
            },
        }
        if tuple(verified) == tuple(range(4)):
            rows = tuple(verified[index] for index in range(4))
            global_lower = certified_arb_global_lower(rows)
            result["certified_global_lower"] = str(global_lower)
    else:
        raise AssertionError(f"unhandled command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
