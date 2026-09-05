# Preprint Release v0.3.0

## Main Result

This release proves

```text
c_E > 0.38055925
```

for the Erdos minimum-overlap constant.

The project-original contribution is a replacement certificate for the two
central mean bins. The proof cites Price's publicly released Arb-certified
bounds for the other 170 bins.

## Verification

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

## Citation And Archive

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
