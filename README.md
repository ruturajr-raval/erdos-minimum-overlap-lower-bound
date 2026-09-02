# Erdos Minimum-Overlap Lower Bound

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22260847.svg)](https://doi.org/10.5281/zenodo.22260847)

A reproducible verification, proof-audit, and certificate-search toolkit for
Erdos's 1955 minimum-overlap problem.

This repository authenticates and replays the licensed Station certificate
establishing `c_E > 0.380552`, implements a separate Python and Arb
verification that does not invoke or link against the retained MPFI verifier,
audits the proof reduction, and records search routes toward stronger bounds.

The supported claim is reproducibility of the Station certificate under two
implementations. This project does not claim the Station bound as
project-original, independently validate the repository-only
`c_E > 0.38055470` claim, or determine `c_E`.

## The Problem

Partition the integers

```text
{1, 2, ..., 2N} = A disjoint-union B
```

into two sets of equal size. For an integer shift `x`, define

```text
O_x(A, B) = number of pairs (a, b) in A x B with a - b = x.
```

Equivalently, `O_x(A, B)` is the size of the overlap between `A` and the
translate `B + x`. Let

```text
M(N) = min over balanced partitions of max over x of O_x(A, B).
```

The asymptotic minimum-overlap constant is

```text
c_E = limit as N tends to infinity of M(N) / N.
```

The question is to determine `c_E`.

In plain language: no matter how evenly and cleverly the integers are divided
into two camps, some translation of one camp must overlap the other many times.
The constant `c_E` measures the smallest unavoidable peak overlap.

## Background And Research Status

Paul Erdos posed the problem in 1955 and initially conjectured that the answer
was `1/2`. The exact constant was still unknown when this project began on
2026-09-01, more than seven decades later.

Several long-lived gaps shaped the problem:

The table distinguishes peer-reviewed results, preprints, and repository-only
computational claims. Its status date is 2026-09-01.

| Year | Development | Evidence status |
| ---: | --- | --- |
| 1955 | Erdos posed the problem, proved the elementary upper bound `c_E <= 1/2`, and conjectured equality. | Published paper |
| 1959 | Moser established the classical lower bound `c_E >= 0.35639395869...`. | Published paper |
| 1996 | Haugland, using a theorem of Swinnerton-Dyer, established the continuous optimization framework and a substantially better upper construction. | Published paper |
| 2016 | Haugland improved the upper bound to `0.3809268534330870`. | Preprint |
| 2022 | White raised the lower bound to `0.379005`, ending a lower-bound benchmark that had lasted about 63 years. | Preprint |
| 2025-2026 | Larger step-function constructions reduced the reported upper bound further, to approximately `0.380856`. | Preprint |
| 2026 | New interval-certified lower-bound work reached `0.37912`. | Preprint |
| 2026 | Chung et al. released the Station certificate establishing `c_E > 0.380552`. | Preprint and Apache-2.0 certificate |
| 2026 | A separate repository claimed `c_E > 0.38055470`. | Repository-only computational claim |

As of the 2026-09-01 audit, recent preprints reported an upper bound near
`0.380856`. The Station paper reported `c_E > 0.380552` and released the
four-row interval certificate audited here. A separate repository claimed
`c_E > 0.38055470`. This project reproduced that repository's checker output
but has not independently reimplemented or verified the stronger claim. The
repository declared no license, so no source code, certificate data, or proof
text was copied.

For this project's search, `0.38055470` is used as a conservative internal
comparison threshold. It is not presented here as an independently established
record. Compared with the reported upper construction `0.380856`, it leaves a
numerical interval of `0.00030130`, subject to independent confirmation of the
stronger lower claim. The exact constant and extremal structure remain open.

## What This Project Did

The work was organized around a strict separation between mathematical claims,
reproduction evidence, and exploratory computation.

1. Authenticated the licensed Station v2 certificate and pinned every retained
   artifact by commit and SHA-256 digest.
2. Replayed the four-row Station certificate with its original MPFI verifier,
   recovering the certified bound
   `c_E > 0.380552257389830222107376462494358...`.
3. Built a separate Python, FLINT, and Arb verifier for the licensed Station
   certificate. It does not invoke or link against the retained MPFI verifier,
   and it independently certifies the same released claim.
4. Audited the discrete-to-continuous reduction, Fourier identities, dual
   inequalities, positive-part integration, and the strictness argument.
5. Replayed the stronger `c_E > 0.38055470` prior-art checker over all 172 mean
   bins using the source repository's original checker. No unlicensed source,
   certificate, report, or proof text is vendored or reused in the project
   implementation.
6. Hardened unsafe checker boundaries. In particular, the project wrapper
   rejects non-finite values, duplicate fields, negative budgets, and
   over-budget rows before invoking the preserved reference executable.
7. Diagnosed why the licensed Station search family does not yet clear the
   stronger threshold and localized the active low-mean bottleneck.
8. Ranked concrete next search routes and recorded acceptance gates for any
   future certificate.

## What Was Achieved

This project resolved a reproducibility and trust question, not the full Erdos
problem.

| Question | Outcome |
| --- | --- |
| Is the licensed Station `c_E > 0.380552` result reproducible? | Yes. |
| Does an independent arithmetic implementation agree? | Yes. |
| Does the proof reduction support the certificate semantics? | Yes, for the audited framework. |
| Can the stronger public `0.38055470` checker reproduce its own claim? | Yes, over all 172 bins. |
| Has that stronger claim been independently reimplemented here? | No. |
| Did this project prove a new lower bound? | No. |
| Did this project determine `c_E`? | No. |

The main deliverable is a trustworthy baseline from which a genuinely new
certificate can be judged. It also prevents two common failure modes in
computer-assisted mathematics: mistaking a successful program run for an
independent proof, and claiming novelty below an existing but poorly indexed
result.

This work is sufficient for release as a reproducibility and proof-audit
artifact. It is not sufficient to announce a new mathematical result or a
solution of the minimum-overlap problem.

## Why It Matters

Every lower-bound improvement strengthens a universal statement about all
balanced partitions of consecutive integers. It proves that repeated
differences cannot be made rarer than the new constant permits.

The problem also connects several areas:

- additive combinatorics through repeated differences and difference sets;
- harmonic analysis through convolution and Fourier constraints;
- discrepancy and extremal set theory through unavoidable imbalance;
- convex and semidefinite optimization through lower-bound relaxations;
- rigorous numerics through interval-certified dual witnesses.

The exact value would identify the true worst-case overlap behavior and settle
a classical problem that has resisted both structural and computational
methods since 1955.

The verification machinery has broader use beyond this constant. The same
pattern can certify sharp inequalities, audit externally produced numerical
proofs, and separate exploratory optimization from theorem-grade evidence.

## What Remains

The following gates remain open:

- independently reimplement and verify the stronger `0.38055470` certificate;
- produce a project certificate strictly above `0.38055470`;
- close or materially narrow the gap to the best upper construction;
- determine whether the current separable-frequency relaxation has reached a
  structural ceiling;
- obtain independent mathematical review before any public theorem claim;
- formalize the finite certificate theorem in a proof assistant if the search
  produces a durable record.

## Limitations

- This repository has not proved a project-original lower bound and has not
  determined the exact value of `c_E`.
- The `c_E > 0.38055470` prior-art result has been replayed only with its
  original checker. It has not yet been independently reimplemented here.
- The current search is limited to particular dual witnesses, frequency
  families, discretizations, and interval-arithmetic formulations. Failure
  within those families would not prove that a stronger bound is impossible.
- Numerical experiments are exploratory until converted into finite
  certificates accepted by two independent directed-arithmetic verifiers.
- The novelty audit is dated 2026-09-01 and can become obsolete as new papers,
  repositories, or unpublished results appear.
- No project-original theorem or certificate has yet received independent
  external mathematical review or formal verification.

These limits mean that the repository currently supports reproducibility and
future search, not an announcement that the 1955 problem has been solved.

## Claim Scope

The supported claim is limited to authenticated replay, independent
verification of the licensed Station certificate, audit of the proof
reduction, checker-hardening findings, and documented search routes. This
repository does not claim a project-original lower bound or a solution of the
problem.

Announcing a new mathematical result requires a project-original theorem that
clears the novelty threshold, passes independent MPFI and Arb verification,
survives mutation and semantic proof audits, is checked against a refreshed
literature search, and receives external mathematical review.

For a genuine new bound, the preferred public record is a versioned repository
release plus a dated preprint containing the theorem, proof reduction,
certificate digest, verification instructions, and comparison with prior art.

## Criteria For A New Result

If a new bound passes every gate, the project will:

1. Freeze the source, certificate, hashes, toolchain, and expected outputs in a
   signed versioned release.
2. Archive that release in a durable research repository with a persistent
   identifier.
3. Publish a dated preprint explaining the theorem and the independently
   checkable proof.
4. Notify the Erdos Problems maintainers, relevant prior authors, and the
   additive-combinatorics community with the exact claim and verification
   instructions.
5. Submit the work for external mathematical review.

A GitHub commit by itself is not treated as adequate publication or
independent validation.

## Future Directions

The highest-value next experiments are:

1. Enrich the low-mean generator family near `m in [0.0018, 0.0028]`.
2. Optimize row mixtures continuously instead of using a small set of
   hand-written combinations.
3. Make positive-part budget loss part of the optimization objective rather
   than applying a large hardening correction afterward.
4. Add frequencies adaptively from reduced-cost or residual information
   instead of uniformly doubling the frequency grid.
5. Introduce independently derived coupled-frequency or small
   positive-semidefinite
   constraints if the separable relaxation stalls.
6. Require both MPFI and Arb replay, mutation tests, a refreshed prior-art
   search, and external review for every promoted candidate.

Detailed numerical evidence and experiment thresholds are in
[`docs/SEARCH_ROUTES.md`](docs/SEARCH_ROUTES.md).

## Verification Status

| Item | Status |
| --- | --- |
| Station artifact authentication | Passed |
| Station four-row MPFI replay | Passed |
| Separate Python and Arb Station verifier | Passed |
| Station framework semantic audit | Passed for the audited reduction and certificate semantics |
| Stronger prior-art checker replay | Passed, provenance only |
| New result from this project | None |
| Supported claim | Reproducibility and proof-audit artifact; no new theorem |

Candidate improvements are not mathematical results until they pass two
independent directed-arithmetic verifiers, a semantic proof audit, a refreshed
prior-art search, and external review.

## Commands

```bash
make sync
make test
make lint
make typecheck
make verify
make audit
```

See `evidence.json`, `evidence/`, and `docs/` for the machine-readable record,
proof audit, prior-art boundary, and search analysis. `release.yaml` records
artifact reproducibility and theorem-announcement readiness separately.

## References

- [P. Erdos, "Some Remarks on Number Theory", 1955](https://www.renyi.hu/~p_erdos/1955-13.pdf).
- L. Moser, "On the Minimum Overlap Problem of Erdos", 1959.
- J. K. Haugland, "Advances in the Minimum Overlap Problem", 1996.
- [J. K. Haugland, arXiv:1609.08000, 2016](https://arxiv.org/abs/1609.08000).
- [E. P. White, arXiv:2201.05704, 2022](https://arxiv.org/abs/2201.05704).
- [S. Kim et al., arXiv:2606.31182, 2026](https://arxiv.org/abs/2606.31182).
- [Y. Ye et al., arXiv:2604.19341, 2026](https://arxiv.org/abs/2604.19341).
- [R. Chung et al., arXiv:2608.23691, 2026](https://arxiv.org/abs/2608.23691).
- [Erdos Problem 36](https://www.erdosproblems.com/36), accessed
  2026-09-01.
