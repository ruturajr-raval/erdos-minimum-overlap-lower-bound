# Search Routes for `c_E > 0.38055480`

## Scope and Verdict

This analysis uses the vendored Apache-2.0 Station source and retained artifacts
plus this project's recorded prior-art facts. No unlicensed implementation or
certificate content was copied or reused. The external repository was inspected
and its original checker was executed only for provenance replay.

The released Station configuration is not close enough: its extended
floating-point candidate is `0.3805526388024265`, which is
`2.0611975735e-6` below the repository-reported `0.38055470` comparison target and
`2.1611975735e-6` below the campaign target. Certification tightening alone
cannot close that gap because the corresponding directed Station result is only
`3.8141259628e-7` below the floating candidate.

The broader Station SOS-remainder family is nevertheless plausible for a small
improvement. A bounded clean run found fixed-mean candidates above
`0.38055480` near the current bottleneck after optimizing row-mixture weights
that Station currently samples only through a few hand-written schemes. The
same experiment failed to lift the whole low-mean envelope, so a new theorem is
not yet close: the active generator set must first be enriched around
`m = 0.0020` to `0.0023`.

## Numerical Diagnosis

| Quantity | Value | Interpretation |
| --- | ---: | --- |
| Directed Station lower bound | `0.380552257389830222...` | Proof baseline |
| Extended Station floating candidate | `0.3805526388024265` | Still `2.0612e-6` below the repository-reported comparison target |
| Retained E8f hardened-row envelope, no mean-grid pad | `0.3805522780996835` | Minimum at `m = 0.0025665` |
| Retained E8f nominal raw envelope | `0.3805549566519549` | Infeasible before exact-budget downshifts |
| Nominal raw margin above target | `1.566519549e-7` | Too small to survive current hardening |

Uniform frequency densification is strongly saturating. Removing the common
mean-grid pad, the E2f-to-E4f gain is `1.8605114111e-5`, while the E4f-to-E8f
gain is only `1.2954847505e-6`, a ratio of `0.06963`. Persisting that ratio
would leave only about `9.70e-8` of further uniform-comb gain. This extrapolation
is not a bound, but it makes a brute-force E16f run low value.

The nominal E8f objectives are misleading without budget enforcement. At
`m = 0`, the retained exact-budget downshift is `1.6059e-6`; at `m = 0.0026`
it is `7.9389e-6`. Recovering enough of the nominal raw envelope to prove the
target would require total loss below `1.57e-7`.

## Bottleneck Region

The directed certificate's first two rows meet at `m = 0.00259038`, where the
global lower bound is attained. The bounded experiments show a wider structural
bottleneck:

- An optimized SOS row at `m = 0.0025665` moves the envelope minimum left to
  `m = 0.00216178`.
- Further greedy rows move it to approximately `m = 0.00201`, where the tested
  family stalls near `0.38055271`.
- The prior-art replay's worst central bins cover `[-0.003125, 0]` and
  `[0, 0.003125]`, consistent with the same low-mean obstruction.

The practical search region is therefore `m in [0.0018, 0.0028]`, not only the
released Station split point.

## Bounded Diagnostic Results

All values in this section are candidate-generation evidence, not proofs.

At `m = 0.0025`, the current `uniform_top4` SOS scheme with 440 selected terms
gave `0.380554298671`. Reducing to 220 terms improved it to
`0.380554378921`; 880 and 1320 terms were numerically much worse. More terms
without adaptive selection are not useful.

A deterministic row-mixture scan at `m = 0.00259038` found weights

```text
(0.2763721639, 0.2886587654, 0.0777568734, 0.3572121973)
```

on the top four active rows. Station's floating midpoint/Lipschitz evaluator
reported `0.380554987385`. Its 80-digit root-isolated replay reported
`0.380555030083`, which is `2.3008e-7` above the campaign target.

That replay is still not proof evidence. The optimizer returned a nonconverged
status, and root discovery reported `22,299` same-sign cells that were not
rigorously excluded from containing tangencies or paired roots. Independent
MPFI or Arb verification is mandatory.

One such quadratic row raises the retained global envelope only to
`0.380552552399`, with the minimum moving to `m = 0.00222614`. A five-step
greedy experiment then stalled at `0.380552706411` near `m = 0.00201`.
Pointwise success at the old split therefore does not yield a global result.

## Ranked Routes

| Rank | Route | Expected value | Compute cost | Certification difficulty |
| ---: | --- | --- | --- | --- |
| 1 | Enrich low-mean E8f generators and optimize mixture weights continuously | High | Medium | High |
| 2 | Hardening-aware SOC optimization with positive-part budget cuts | Medium-high | Medium-high | Medium-high |
| 3 | Adaptive frequency column generation instead of uniform E16f | Medium | Medium | Medium |
| 4 | Add independently derived coupled-frequency or PSD generator inequalities | High long-term | High | High |
| 5 | Tighten only mean coverage or directed arithmetic | Low | Low | Low |

### 1. Enriched Generator Simplex

The retained generator NPZ already contains E8f arrays at eight anchors, but
`NCONV_E8F_ROW_ANCHORS` loads only four: `0`, `0.0026`, `0.003`, and
`0.004475`. Load all retained anchors and replace the fixed one-hot/uniform
mixtures with reproducible simplex sampling or a constrained outer optimizer.
This directly addresses the observed stall around `m = 0.0020`.

### 2. Hardening-Aware Optimization

The current optimizer solves a gridded surrogate and applies a potentially
large exact-budget downshift afterward. Iterate between the SOC solve and
positive-part root analysis, adding cuts that enforce the budget during
optimization. This route should be combined with Route 1; the nominal raw
headroom is too small for hardening improvements alone.

### 3. Adaptive Frequency Columns

The E4f-to-E8f gain collapse argues against a uniform E16f comb. Instead, add
frequencies at the largest reduced-cost or residual locations of the current
dual, re-solve, and stop when every omitted column has nonpositive reduced
cost within a declared tolerance.

### 4. New Generator Inequalities

If the enriched simplex still stalls near `m = 0.0020`, derive additional
project-original constraints coupling two or more Fourier frequencies, for example
small Toeplitz/Bochner PSD blocks or completion-of-squares identities with
cross terms. This is the likely route past a true separable-frequency ceiling.

### 5. Certification Improvements

Use analytic quadratic-envelope minimization and independent outward-rounded
positive-part integration after a candidate clears the target. This cannot
create novelty by itself because Station's retained floating global candidate
is more than `2e-6` below the repository-reported comparison target.

## Recommended First Experiment

Run a ten-minute enriched-generator simplex tranche in an isolated Apache
source copy.

Use these exact temporary configuration changes:

```text
source/soc_sos_remainder_pilot.py
NCONV_E8F_ROW_ANCHORS =
    (0.0, 0.001, 0.002, 0.0024, 0.0026, 0.0028, 0.003, 0.004475)

source/soc_sos_dual.py
ACTIVE_ROW_COUNT = 8
TERM_LIMIT = 220
OPT_GRID_N = 6001
CERT_PARTITIONS = 240000

source/soc_sos_dual_global.py
ANCHORS =
    (0.0018, 0.0019, 0.0020, 0.0021, 0.0022, 0.0023, 0.0024,
     0.0025, 0.0025665, 0.00259038, 0.0026, 0.00265, 0.0027, 0.0028)
GLOBAL_START_SCALES = (0.25, 0.5, 1.0, 1.5)
GLOBAL_MAXITER = 500
REFINED_PARTITIONS = 6000000
DOMAIN_PARTITIONS = 2000000
```

Extend `_global_lambda_schemes` with the uniform and front-loaded seeds, the
two observed weight vectors below, eight seeded Dirichlet samples on the top
four rows, and eight on the top six rows. Use
`np.random.default_rng(20260901)`.

```text
(0.1879206888, 0.0609005406, 0.3504977865, 0.4006809841)
(0.2763721639, 0.2886587654, 0.0777568734, 0.3572121973)
```

Run it without modifying the research repository:

```bash
ROOT="$(git rev-parse --show-toplevel)"
RUN=/tmp/station-comparison-probe-20260901
rm -rf "$RUN"
mkdir -p "$RUN"
cp -R "$ROOT/upstream/station/witness_generation/." "$RUN/"
cd "$RUN"

"$ROOT/.venv/bin/python" -u - <<'PY' | tee comparison-probe.log
from pathlib import Path
import sys

sys.path.insert(0, "source")
import soc_sos_dual_global as search

search.run_global_analysis(
    max_total_seconds=600.0,
    out_json=Path("outputs/comparison_probe.json"),
)
PY
```

Promote the route only if the complete floating envelope exceeds
`0.38055530`, leaving at least `5e-7` above the campaign target for rounding
and verification loss. Then export fixed decimal rows and require both the
project's separate Arb verifier and the MPFI verifier to pass. Until those
checks pass, label every output `candidate_only`; neither optimizer convergence
nor mpmath root isolation is a mathematical proof.
