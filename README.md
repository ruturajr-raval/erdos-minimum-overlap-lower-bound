# Erdos Minimum-Overlap Lower Bound

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22260847.svg)](https://doi.org/10.5281/zenodo.22260847)

This repository proves the certified lower bound

```text
c_E > 0.38055925
```

for the Erdos minimum-overlap problem.

The project-original contribution is an even replacement certificate for the
two central mean bins. The other 170 mean bins use Liam Price's previously
publicly released Arb-certified bounds. The new center certificate is
accepted by two separate directed-arithmetic implementations:

- Python with python-flint and Arb
- C with MPFI, MPFR, and GMP

The exact value of `c_E` remains open.

## The Problem

Partition

```text
{1, 2, ..., 2N} = A disjoint-union B
```

into two sets of size `N`. For an integer shift `d`, count the pairs

```text
(a, b) in A x B with b - a = d.
```

Let `R(A, B)` be the largest such count over all shifts, and minimize it over
all balanced partitions. The asymptotic constant is

```text
c_E = liminf as N tends to infinity of
      (1/N) min over balanced partitions R(A, B).
```

The question is to determine `c_E`.

In plain language, every balanced two-coloring of consecutive integers has a
translation where many opposite-colored points coincide. The constant measures
the smallest unavoidable peak overlap.

## Main Result

The manuscript in [`paper/main.tex`](paper/main.tex) proves:

> **Theorem.** The Erdos minimum-overlap constant satisfies
> `c_E > 0.38055925`.

The proof separates the mean of the continuous overlap density into 172 bins.

| Mean region | Certificate used | Verified denominator upper |
| --- | --- | ---: |
| Central bins 85 and 86, `|mu| <= 1/320` | Project-original certificate | `2.627711172296609116` |
| Other 170 bins | Price's publicly released certificate | `2.627538530873375791` |
| Required threshold | `1 / 0.38055925` | `2.627711716375308181...` |

Both denominator bounds are strictly below the threshold. The finite maximum
over all 172 bins is therefore also strictly below the threshold, which gives
the uniform strict lower bound.

## Background

Paul Erdos posed the problem in 1955 and conjectured that the constant was
`1/2`. The exact value has resisted structural and computational methods for
more than seventy years.

Selected lower-bound developments are:

| Year | Result | Status |
| ---: | --- | --- |
| 1959 | Moser proved the classical lower bound `0.35639395869...` | Published |
| 2022 | White raised the lower bound to `0.379005` | Preprint |
| 2026 | Chung et al. released a certificate for `c_E > 0.380552` | Preprint and Apache-2.0 artifacts |
| 2026-07 | Price publicly released a repository certificate for `c_E > 0.38055470` | Public computational result |
| 2026-09-03 | Deng published a certified result `c_E > 0.380557` | Repository, preprint, and Zenodo archive |
| 2026-09-04 | This project certifies `c_E > 0.38055925` | This repository |

The dated prior-art audit found no public result above the effective numerical
capability of Deng's retained center certificate, approximately
`0.380558179527858...`. The present certified target exceeds that comparison
point by approximately `1.07047e-6`.

Recent upper-bound constructions remain near `0.380856`, so a numerical gap of
about `0.00029675` remains.

## New Certificate

For the central mean range `|mu| <= 1/320`, the certificate uses:

- one exact second-moment inequality;
- 107 pointwise Fourier inequalities
  `C_xi <= sinc(xi)^2`;
- one Parseval energy inequality truncated at order `100`;
- nonnegative exact-decimal multipliers.

These rows define an even function

```text
q(t) = 1
     + lambda_2 (B_2 - t^2)
     + sum_xi lambda_xi (sinc(xi)^2 - cos(xi t))
     + lambda_P (1/2 + sum_{n=1}^{100} cos(n pi t)).
```

The positive-part dual principle gives

```text
||p||_infinity >= 1 / integral max(q(t), 0) dt.
```

The certificate file is
[`certificates/center-038055925.tsv`](certificates/center-038055925.tsv), with
SHA-256:

```text
b02a45a645337c74215a365e82f403990eeb9413e3f8771e719e5e5397da39e8
```

Frequencies and multipliers are interpreted as exact rational decimals.
Each `sinc(xi)^2` right-hand side is the exact transcendental value, enclosed
independently by directed arithmetic in each verifier.

## Verification

### Python-Arb

The Python verifier:

- parses the canonical certificate without floating-point conversion;
- computes the analytic bounds with python-flint and Arb;
- encloses `q`, `q'`, and `q''` on adaptive cells using Taylor's theorem;
- integrates certified-positive cells with an interval antiderivative;
- charges unresolved terminal cells by a rigorous upper rectangle.

At 256-bit precision it reports:

```text
D_upper = 2.627711172296609115765958739218722735...
margin  = 0.000000544078699065548777402393917083...
```

### MPFI/C

The independent C verifier has its own:

- strict LF-ASCII parser;
- exact decimal-to-rational conversion;
- MPFI and MPFR interval calculations;
- adaptive traversal and accounting;
- endpoint extraction and strict target comparison.

At 256-bit precision it reports:

```text
D_upper = 2.627711172296609115765958701268201763538
margin  = 0.0000005440786990655487774403444380553601380208
```

The two implementations agree beyond the precision needed for the theorem.
Their shared boundary is limited to the certificate bytes, analytic formulas,
Taylor enclosure argument, and elementary antiderivative.

## Reproduce

Prerequisites:

- Python 3.12
- `uv`
- a C compiler
- GMP, MPFR, and MPFI development libraries

Run:

```bash
make sync
make test
make lint
make typecheck
make verify
make audit
```

Run the new center checks directly:

```bash
uv run minoverlap verify-center \
  certificates/center-038055925.tsv

uv run minoverlap verify-center-mpfi \
  certificates/center-038055925.tsv
```

The complete machine-readable record is in:

- [`evidence/center-038055925-verification.json`](evidence/center-038055925-verification.json)
- [`evidence/noncentral-038055925-replay.json`](evidence/noncentral-038055925-replay.json)
- [`evidence/noncentral-038055925-report.csv`](evidence/noncentral-038055925-report.csv)
- [`evidence/noncentral-038055925-report.json`](evidence/noncentral-038055925-report.json)
- [`evidence/noncentral-038055925-report.log`](evidence/noncentral-038055925-report.log)
- [`evidence.json`](evidence.json)

## What We Claim

- The frozen project center certificate rigorously covers both central mean
  bins.
- Two independently implemented directed-arithmetic verifiers accept it.
- Price's other 170 bins were replayed at the same target and all passed.
- Together these finite certificates establish `c_E > 0.38055925`.
- The center certificate and verification implementations are
  project-original work by Ruturaj R Raval.

## What We Do Not Claim

- We do not determine the exact value of `c_E`.
- We do not claim the retained multipliers are optimal.
- We do not claim Price's noncentral certificate as project-original work.
- We do not redistribute Price's unlicensed source or certificate files.
- We do not treat repeated runs of one implementation as independent
  verification.
- Independent external mathematical review is not yet complete.

## Significance

Every lower-bound improvement strengthens a universal theorem over all balanced
partitions of every sufficiently large interval. It rules out an additional
range of hypothetical low-overlap constructions.

The method also contributes a reusable computer-assisted proof pattern:

- separate optimization from verification;
- freeze exact certificate semantics;
- require independent arithmetic implementations;
- bind evidence by cryptographic hashes;
- preserve dependency and licensing boundaries;
- state numerical and mathematical nonclaims explicitly.

The same architecture applies to extremal combinatorics, Fourier inequalities,
rigorous optimization, and other finite-certificate proofs.

## Remaining Work

The main mathematical problem remains open. High-value next directions include:

1. Continue reduced-cost column generation and test whether the current
   Fourier relaxation has a structural ceiling.
2. Add coupled-frequency or positive-semidefinite constraints.
3. Narrow the remaining gap to the best upper construction.
4. Seek independent external reproduction and peer review.
5. Formalize the finite analytic reduction and certificate semantics in a
   proof assistant.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `certificates/` | Frozen project certificate |
| `src/minoverlap/center_certificate.py` | Python-Arb center verifier |
| `verification/center_mpfi.c` | Independent MPFI/C center verifier |
| `paper/` | Proof manuscript |
| `evidence/` | Machine-readable verification and provenance records |
| `docs/` | Prior-art, proof, and search analysis |
| `upstream/station/` | Licensed Station reproduction baseline |
| `research/` | Claim and release-gate records |

## Licensing

Project-original software, certificate data, and documentation are released
under Apache-2.0. The retained Station artifacts preserve their Apache-2.0
provenance.

Price's noncentral source package is cited and hash-pinned but is not included
because no license was declared at the audited commit.

## References

- P. Erdos, "Some Remarks on Number Theory", 1955.
- L. Moser, "On the Minimum Overlap Problem of Erdos", 1959.
- E. P. White, arXiv:2201.05704, 2022.
- R. Chung et al., arXiv:2608.23691, 2026.
- L. Price, `Leeham06972452/erdos-36-lower-bound`, pinned 2026 commit.
- H. Deng, DOI `10.5281/zenodo.22279894`, 2026.
