# Release Dossier v0.3.0

## Release Identity

| Field | Value |
| --- | --- |
| Title | The Erdos Minimum-Overlap Constant Exceeds 0.38055925 |
| Tagged release | [`v0.3.0`](https://github.com/ruturajr-raval/erdos-minimum-overlap-lower-bound/releases/tag/v0.3.0) |
| Release date | 2026-09-05 |
| Audited release commit | `c58d520a72dc85dc14dd3c7a5c07d38e7080b589` |
| Certified clean-checkout commit | `bc4115ff1108962fe19af30a88bf1ca7a0adddc1` |
| Version DOI | [`10.5281/zenodo.22313820`](https://doi.org/10.5281/zenodo.22313820) |
| Concept DOI | [`10.5281/zenodo.22260847`](https://doi.org/10.5281/zenodo.22260847) |
| Archive status | Published Zenodo snapshot recorded in `release.yaml` |
| License | Apache-2.0 for project-original material |

## Claim-Safe Public Summary

Release `v0.3.0` establishes `c_E > 0.38055925`. The project-original
contribution is an even replacement certificate for the two central mean
bins, accepted by independently implemented Arb and MPFI verifiers. The other
170 bins use Price's cited, hash-pinned certificate and were replayed at the
same target. The exact value remains open.

## Supported Result

This release proves

```text
c_E > 0.38055925
```

for the Erdos minimum-overlap constant.

The project-original contribution is a replacement certificate for the two
central mean bins. The proof cites Price's publicly released Arb-certified
bounds for the other 170 bins.

## Verification And Evidence

The frozen center certificate is accepted by:

1. a Python implementation using python-flint and Arb;
2. an independent C implementation using MPFI, MPFR, and GMP.

Both use exact decimal certificate semantics, directed transcendental
evaluation, adaptive Taylor classification, and rigorous positive-part
integration. Their parser, arithmetic, traversal, accounting, and endpoint
code are independently implemented.

All 170 reused Price bins were rerun at target `0.38055925` and passed.

## Artifacts

- `certificates/center-038055925.tsv`
- `src/minoverlap/center_certificate.py`
- `verification/center_mpfi.c`
- `paper/main.tex`
- `paper/ARXIV_METADATA.md`
- `tools/build_arxiv_bundle.py`
- `evidence/center-038055925-verification.json`
- `evidence/noncentral-038055925-replay.json`
- `evidence/noncentral-038055925-report.csv`
- `evidence/noncentral-038055925-report.json`
- `evidence/noncentral-038055925-report.log`

The center certificate SHA-256 is:

```text
b02a45a645337c74215a365e82f403990eeb9413e3f8771e719e5e5397da39e8
```

## Manifest And Asset Verification

Use `release-manifest.sha256` from a clean checkout of tag `v0.3.0` to verify
the tracked release files. `release.yaml` records the audited release commit,
tag-protection state, source and PDF asset names, sizes and SHA-256 values, and
the Zenodo repository snapshot name, size, MD5, and SHA-256.

## Reproduction

```bash
make sync
make test
make lint
make typecheck
make build
make verify
make audit
make paper-build
make paper-bundle
```

## Claim Boundary

This release claims a new certified lower bound. It does not claim:

- the exact value of `c_E`;
- optimality of the retained multipliers;
- project originality for Price's noncentral certificate;
- redistribution rights for Price's unlicensed source package;
- completion of independent external mathematical review.

## Provenance Boundary

The center certificate and both center verifiers are project-original. Price's
source repository, commit, certificate digest, verifier digest, command, and
observed outputs are recorded, but the unlicensed source package and
certificate are not redistributed. Licensed Station baseline material remains
under its upstream notices in `upstream/station/`.

## Review Status

Internal mathematical-semantics, prior-art, numerical, verifier, and
noncentral-coverage audits are recorded as passed in `review.yaml`.
`research/release-gate.json` records a release decision after clean-checkout
replay. Independent external mathematical review remains pending.

## Archive And Citation

Citation metadata is in `CITATION.cff`. The exact v0.3.0 release is archived
at version DOI:

```text
10.5281/zenodo.22313820
```

All repository versions are collected under the stable concept DOI:

```text
10.5281/zenodo.22260847
```

The certified v0.2.0 artifact release is archived at version DOI
`10.5281/zenodo.22308924`. The manuscript cites that immutable proof-artifact
snapshot.

Historical release scope is summarized in `RELEASE_NOTES.md`.

## Next Acceptance Gate

Any stronger theorem must exceed `0.38055925`, retain complete coverage of all
172 mean bins, pass both independent directed-arithmetic verifiers and a clean
checkout replay, refresh the prior-art comparison, and preserve all dependency
and licensing boundaries. External mathematical review should be completed
before representing a later result as externally reviewed.
