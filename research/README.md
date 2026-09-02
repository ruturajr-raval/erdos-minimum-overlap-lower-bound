# Research Workbench

This directory records the search for a project-original certified lower bound
for the Erdos minimum-overlap constant.

The current repository release is a reproducibility and proof-audit artifact.
It does not establish a new lower bound. Work in this branch is promoted only
after it produces a claim that is both stronger than the refreshed prior-art
frontier and independently replayable from retained evidence.

## Active Target

Construct and rigorously certify a lower bound above the strongest verified
public result. The comparison threshold must be refreshed immediately before a
novelty claim is made.

The initial search family uses all eight retained `E8f` anchors, continuous
mixtures, hardening-aware optimization, and adaptive column generation. A
rigorous upper bracket will be computed for this family before moving to a
larger semidefinite relaxation.

## Records

- `claim.yaml` defines the exact scope of the candidate result.
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

