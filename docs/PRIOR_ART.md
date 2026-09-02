# Prior-Art Record

## Current Frontier

The strongest repository-reported target located during the 2026-09-01 search
is `c_E > 0.38055470`, posted in
`Leeham06972452/erdos-36-lower-bound` at commit
`6bc610e40083ef61a40966dfb5d38612cabc4c5b` on 2026-07-01.

Its original Arb checker was rerun over all 172 mean bins. Every bin passed. The central
bins 85 and 86 were tight, with the reported worst denominator upper ball centered at
`2.627743114828466248...`; the repository-reported target permits
`1 / 0.38055470 = 2.627743133904271843...`.

Its original checker replayed successfully. This establishes only that the
public checker reproduces its own target; the claim has not been independently
reimplemented here.

## Licensing Boundary

No license was declared in that repository at the inspected commit. Consequently:

- no source code, certificate JSON, proof text, or generated report was copied here;
- hashes, commit metadata, mathematical facts, and independently observed replay outputs
  are recorded for provenance;
- any project implementation of the same mathematical framework must be independently
  implemented without copying unlicensed source material.

The licensed Station v2 source remains the implementation baseline for this project.

## Novelty Rule

A project result must exceed `0.38055470`, not merely the older Station target. The first
campaign target is therefore `c_E > 0.38055480`, subject to all certification and review
gates.
