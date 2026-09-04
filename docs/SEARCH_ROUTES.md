# Search Outcome and Future Routes

## Outcome

Adaptive cosine-frequency column generation produced the retained center
certificate for

```text
c_E > 0.38055925.
```

The search optimized the exact positive-part objective

```text
D(lambda) = integral from -2 to 2 of max(q_lambda(t), 0) dt
```

over nonnegative multipliers. Analytic antiderivatives and gradients were used
for discovery. None of those floating calculations is trusted by the proof.

## Progression

Starting from the strongest located 69-row center certificate, fixed-frequency
reoptimization gave only a small gain. Reduced-cost scans over the continuous
cosine-frequency family then found strong omitted columns.

| Stage | Cosine rows | Discovery reciprocal |
| --- | ---: | ---: |
| Located prior center certificate | 67 | `0.380558179562...` |
| Fixed-frequency reoptimization | 67 | `0.380558187516...` |
| Column round 1 | 77 retained | `0.380558843921...` |
| Column round 2 | 86 retained | `0.380559139365...` |
| Column round 3 | 96 retained | `0.380559265104...` |
| Column round 4 | 107 retained | `0.380559328796...` |
| Frozen theorem target | 107 | `0.38055925` |

The retained target leaves a denominator margin of approximately `5.44e-7`
for exact-decimal semantics and directed verification.

## Independent Numerical Stress Test

An independent high-precision audit found:

- 120 roots and 60 positive intervals;
- agreement across mesh steps `2e-5`, `4e-6`, and `1e-6`;
- the same roots from derivative-root isolation;
- root-free quadrature agreement within `2e-14`;
- narrowest positive interval width approximately `5.46e-4`;
- shallowest positive peak approximately `9.22e-11`.

No missed positive island or objective inconsistency was found.

## What Worked

The decisive step was column generation. For the indicator of the current
positive set, the reduced cost of a new cosine row can be evaluated from the
exact interval endpoints:

```text
gradient(xi)
  = integral over q > 0 of
    (sinc(xi)^2 - cos(xi t)) dt.
```

Strongly negative reduced costs identify valid rows that can lower the
positive-part integral. Reoptimizing all multipliers after each batch gave
orders of magnitude more progress than tightening the existing frequencies.

## What Is Not Established

- The multiplier vector is not proven optimal.
- The continuous cosine-row relaxation is not proven exhausted.
- Failure of future columns would not prove the exact constant.
- The discovery optimizer stopped at iteration limits, which is irrelevant to
  certificate validity but prevents an optimization claim.

## Next Routes

1. Continue column generation until omitted reduced costs are uniformly small.
2. Optimize several Parseval truncation rows jointly rather than retaining
   only order 100.
3. Add mean-conditioned sine rows and coupled-frequency residual bounds.
4. Introduce small Toeplitz or Bochner positive-semidefinite constraints.
5. Search for a structural characterization of near-extremal overlap
   densities.
6. Formalize the analytic reduction and certificate checker in a proof
   assistant.

Any future promotion must retain the same standard:

- exact certificate bytes and hashes;
- two independently implemented directed-arithmetic verifiers;
- complete mean-bin coverage;
- refreshed prior-art comparison;
- explicit dependency, limitation, and nonclaim records.
