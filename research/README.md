# Research Record

This directory records the search for a project-original certified lower bound
for the Erdos minimum-overlap constant.

The maintained branch contains a certified project-original center
certificate. Combined with Price's published noncentral bins, it establishes
`c_E > 0.38055925`. The artifact release and clean-checkout replay are
complete. Release `v0.3.0` publishes the result with a self-contained
technical report and an explicit dependency boundary.

## Current Target

Improve the certified lower bound beyond `c_E > 0.38055925` without weakening
its provenance or claim boundaries. The retained center certificate uses
adaptive cosine-frequency column generation and is accepted by independent
Python-Arb and MPFI/C implementations. Stronger work must cover all 172 bins
and pass the same dual-verifier and clean-replay gates.

## Records

- `claim.yaml` defines the exact scope of the supported result.
- `release-gate.json` records which promotion requirements have been met.
- `run.schema.json` defines the minimum metadata for retained computations.
- `/.research-artifacts/` holds local exploratory outputs and is not tracked.

Every retained certificate must identify its generator commit, exact inputs,
arithmetic backend, verification command, and SHA-256 digest. Discovery output
is not evidence until a separate verifier accepts it with rigorous arithmetic.

## Promotion Standard

A result is ready for promotion only when all of the following hold:

1. The prior-art search has been refreshed and documented.
2. The numerical improvement exceeds the certified uncertainty by a
   conservative margin.
3. Two independent rigorous verification paths accept the certificate.
4. A clean checkout can replay the retained evidence.
5. The theorem statement distinguishes project-original work from reproduced
   results.
6. The manuscript and repository state the limitations and remaining gap.
7. Independent mathematical review has been requested and any material
   objections have been resolved.
