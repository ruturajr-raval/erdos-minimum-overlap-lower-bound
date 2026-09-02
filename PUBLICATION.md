# Release v0.1.0

## What Was Done

This release authenticates and replays the licensed Station certificate for
Erdos's minimum-overlap problem, implements a separate Python and Arb
verification, audits the proof reduction, and records reproducible routes
toward stronger bounds.

## Supported Claim

The Station certificate establishing `c_E > 0.380552` is reproducible with
the retained MPFI verifier and with a separate implementation that does not
invoke or link against it.

## Not Claimed

- The Station bound is not claimed as project-original.
- The repository-only `c_E > 0.38055470` claim is replayed with its original
  checker but is not independently validated here.
- No new lower bound or determination of `c_E` is claimed.

## Evidence

`evidence.json` records source commits, artifact digests, replay reports, and
claim boundaries. `docs/PROOF_AUDIT.md` records the audited mathematical
reduction. `THIRD_PARTY_NOTICES.md` records the licensing and modification
boundary. `release-manifest.sha256` authenticates the principal release files.

## Reproduction

```bash
make sync
make test
make lint
make typecheck
make build
make verify
make audit
```

## Limitations And Remaining Work

The stronger repository-reported comparison target still requires a separate
implementation. A project-original result requires a certificate above that
target, two directed-arithmetic verification paths, a refreshed prior-art
audit, and external mathematical review.

## Citation

Citation metadata is provided in `CITATION.cff`. The release metadata in
`.zenodo.json` is prepared for durable archival.
