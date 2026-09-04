# Prior-Art Record

Status date: 2026-09-04.

## Located Lower-Bound Frontier

The prior-art audit found the following recent computational results.

| Date | Source | Stated claim | Verification and licensing notes |
| --- | --- | ---: | --- |
| 2026-07-01 | `Leeham06972452/erdos-36-lower-bound`, commit `6bc610e40083ef61a40966dfb5d38612cabc4c5b` | `c_E > 0.38055470` | Original Arb checker replayed; no declared license |
| 2026-08-24 | Chung et al., arXiv:2608.23691 | `c_E > 0.380552` | Apache-2.0 certificate and later Lean formalization |
| 2026-09-03 | `emerardd/erdos-36-lower-bound-0380557`, commit `0913ca8ebab68927e5f16026ea7c45070634d737` | `c_E > 0.380557` | MIT original material; Price dependency excluded from that license |

Deng's strongest retained Python interval transcript gives

```text
D <= 2.6277191078658615742268756
```

whose reciprocal is approximately

```text
0.3805581795278582246.
```

The transcript capability is stronger than the rounded theorem statement, so
the project used it as the numerical novelty comparison rather than comparing
only with `0.380557`.

No public result above that comparison point was located by the status date.

## Project Comparison

The project theorem is

```text
c_E > 0.38055925.
```

Its margin above the strongest located recorded certificate capability is
approximately

```text
0.0000010704721417754.
```

The project center denominator is approximately

```text
2.627711172296609116,
```

compared with Deng's recorded center denominator

```text
2.627719107865861574....
```

## Price Dependency

The global theorem reuses Price's noncentral mean-bin bounds. The project
reran all 170 reused bins at target `0.38055925`. The largest denominator was

```text
2.627538530873375790...
```

at bin 77, with the reflected bin 94 attaining the same value to the displayed
precision. This is comfortably below

```text
1 / 0.38055925 = 2.627711716375308181....
```

Price's central bins 85 and 86 are not used.

## Licensing Boundary

Price's audited repository declared no license. Consequently:

- no Price source, certificate, proof text, or generated report is included;
- commit identifiers, hashes, mathematical facts, commands, and independently
  observed outputs are retained;
- the project center certificate and both center verifiers are independently
  implemented;
- the manuscript cites Price for the 170 noncentral bins.

Deng's original material is MIT-licensed, but this project did not copy its
certificate or verifier implementation. The mathematical row family and
published numerical facts are credited in the manuscript.

## Novelty Rule

A project claim had to exceed the strongest located retained certificate
capability, not merely an older rounded theorem statement. It also had to:

1. freeze exact certificate semantics;
2. pass two independently implemented directed-arithmetic verifiers;
3. cover all 172 mean bins without gaps;
4. survive a refreshed prior-art search;
5. state the Price dependency and all nonclaims explicitly.

The retained `0.38055925` certificate passes these internal gates. Independent
external review remains pending.
