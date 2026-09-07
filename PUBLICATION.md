# Release Dossier v0.3.1

## Release Identity

| Field | Value |
| --- | --- |
| Title | The Erdos Minimum-Overlap Constant Exceeds 0.38055925 |
| Author | Ruturaj R Raval |
| Affiliation | Independent Researcher |
| ORCID | [0000-0003-4930-8981](https://orcid.org/0000-0003-4930-8981) |
| Tagged release | [`v0.3.1`](https://github.com/ruturajr-raval/erdos-minimum-overlap-lower-bound/releases/tag/v0.3.1) |
| Release date | 2026-09-07 |
| Audited release commit | `965fcdec86a3232ed4895e3180c9c7b3d1a85b77` |
| Archive status | GitHub release and paper-inclusive Zenodo version published; all three public assets downloaded and verified |
| Underlying theorem release | `v0.3.0` |
| Version DOI | [`10.5281/zenodo.22647743`](https://doi.org/10.5281/zenodo.22647743) |
| Concept DOI | [`10.5281/zenodo.22260847`](https://doi.org/10.5281/zenodo.22260847) |
| Patch type | Paper-inclusive archival and documentation patch |
| License | Apache-2.0 for project-original material |

## Claim-Safe Public Summary

Release `v0.3.1` adds an explicitly named compiled paper PDF, deterministic
paper-source archive, and checksum manifest. The theorem, proof,
certificates, data, computations, and claim boundary are unchanged from
`v0.3.0`: `c_E > 0.38055925`, with the exact value still open.

## Supported Result

The underlying theorem release proves

```text
c_E > 0.38055925
```

for the Erdos minimum-overlap constant.

The project-original contribution is a replacement certificate for the two
central mean bins. The proof cites Price's publicly released Arb-certified
bounds for the other 170 bins.

This patch changes only archival packaging and documentation. It introduces
no new theorem, certificate, data, or computation.

The dated 2026-09-04 starting-frontier audit located a strongest stated claim
of `c_E > 0.380557` and a strongest recorded certificate capability of
`0.3805581795278582246`. The certified value in this release is
`0.0000010704721417754` above that recorded capability and `0.00000225` above
the stated threshold.

## Significance

The result strengthens a universal lower bound for the minimum-overlap
problem and isolates the improvement in a small, independently checked
replacement certificate. The certificate-first method, dual-verifier design,
and explicit dependency boundary can be reused in other rigorous finite
optimization arguments. This release does not determine the exact constant
or imply that the retained multipliers are optimal.

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
- `tools/build_release_assets.py`
- `evidence/center-038055925-verification.json`
- `evidence/noncentral-038055925-replay.json`
- `evidence/noncentral-038055925-report.csv`
- `evidence/noncentral-038055925-report.json`
- `evidence/noncentral-038055925-report.log`

The center certificate SHA-256 is:

```text
b02a45a645337c74215a365e82f403990eeb9413e3f8771e719e5e5397da39e8
```

The paper-inclusive release assets are:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `erdos-minimum-overlap-lower-bound-v0.3.1-paper.pdf` | 91,673 | `e3a4dad76eb50244f07425e7c75fad43f155db5244cc2ee2eb49fed8ba69574f` |
| `erdos-minimum-overlap-lower-bound-v0.3.1-paper-source.tar.gz` | 47,883 | `03753cd986592973bd739c546a9a463ca1eed1aec9fc0058475462751ff1a18b` |
| `SHA256SUMS` | 244 | `46945e89783298a43196735b4e3ca0b502841aba55be3cc5998c6598589be92b` |

## Manifest And Asset Verification

Use `release-manifest.sha256` from a clean checkout of tag `v0.3.1` to verify
the tracked release files. Run `make verify-release-assets` to authenticate
the exact three-file set in `dist/release/v0.3.1/`. `release.yaml` records the
asset names, sizes, SHA-256 values, version DOI, concept DOI, and unchanged
mathematical scope.

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
make paper-release
make verify-release-assets
```

## Claim Boundary

The mathematical claim is unchanged from `v0.3.0`. This archival patch does
not claim a new theorem, proof, certificate, data set, or computation. The
underlying result does not claim:

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

Citation metadata is in `CITATION.cff`. The paper-inclusive `v0.3.1` patch is
identified by version DOI:

```text
10.5281/zenodo.22647743
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
