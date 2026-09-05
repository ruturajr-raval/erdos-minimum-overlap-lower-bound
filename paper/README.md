# Manuscript

`main.tex` contains the proof of the certified claim
`c_E > 0.38055925`. `ARXIV_METADATA.md` contains the submission metadata, and
`ARXIV_README.txt` is included in the source bundle.

Build with a standard LaTeX installation:

```bash
make paper-build
```

Build the deterministic, allowlisted arXiv source archive with:

```bash
make paper-bundle
```

The archive is written to
`dist/arxiv/erdos-minimum-overlap-038055925.tar.gz`. It contains the
manuscript, project-original center certificate and checkers, compact evidence
records, license, and an SHA-256 manifest. Price's unlicensed source and
certificate are intentionally excluded.
