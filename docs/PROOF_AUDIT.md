# Proof Audit

Status: complete for the retained `c_E > 0.38055925` certificate and its stated
dependency boundary.

## Discrete-To-Continuous Reduction

For a balanced partition, replace each integer by an interval of width `1/N`.
The continuous overlap is a triangular interpolation of the discrete
difference counts. For a fixed shift, at most two adjacent integer
differences contribute and their triangular weights sum to at most one.
Therefore the continuous overlap supremum is at most the largest discrete
count divided by `N`.

This proves that a universal continuous lower bound transfers in the required
direction to the discrete liminf.

## Center Constraints

For an admissible overlap density `p` with mean `mu`:

- `integral p = 1`;
- `mu` lies in `[-1, 1]`;
- `integral t^2 p(t) dt = 2/3 + mu^2/2`;
- for every real `xi`,
  `integral p(t) cos(xi t) dt <= sinc(xi)^2`;
- for every positive integer `M`,
  `-sum_{n=1}^M integral p(t) cos(n pi t) dt <= 1/2`.

For `|mu| <= 1/320`, the exact second-moment upper bound is

```text
2/3 + 1/(2 * 320^2).
```

All certificate multipliers are nonnegative.

## Exact Certificate Semantics

The canonical certificate is
`certificates/center-038055925.tsv`.

- Decimal frequencies and multipliers are exact rational numbers.
- The right-hand side `sinc(xi)^2` is the exact transcendental value.
- Each verifier encloses that value independently with directed arithmetic.
- The certificate contains one second-moment multiplier, 107 cosine
  multipliers, and one Parseval multiplier of order 100.
- Frequencies are positive, bounded, unique, and strictly increasing.
- The certificate is even and covers both central bins.

## Positive-Part Argument

For valid rows `integral p phi_j <= B_j` and nonnegative multipliers, define

```text
q(t) = 1 + sum_j lambda_j (B_j - phi_j(t)).
```

Then `integral p q >= 1`. Since `p >= 0`,

```text
1 <= ||p||_infinity * integral max(q(t), 0) dt.
```

Thus a rigorous denominator upper bound `D` gives
`||p||_infinity >= 1/D`.

## Directed Integration

Both center verifiers work on `[0, 2]` and double by evenness. On each cell
they enclose `q(c)`, `q'(c)`, and `q''(c)` at the center and use a global upper
bound for `|q'''|`. Taylor's theorem certifies the sign or triggers bisection.

- Certified-negative cells contribute zero.
- Consecutive certified-positive cells are integrated with an elementary
  directed antiderivative.
- An unresolved terminal cell is charged by its width times the positive part
  of a certified upper endpoint.

No floating-point root is trusted by either proof path.

## Independent Implementations

The Python-Arb implementation and MPFI/C implementation independently provide:

- certificate parsers;
- exact decimal conversion;
- interval arithmetic backends;
- adaptive traversal;
- positive and terminal-cell accounting;
- antiderivative evaluation;
- endpoint extraction;
- strict target comparison.

They share only the certificate bytes, analytic formulas, Taylor argument, and
elementary antiderivative.

The conservative retained denominator is

```text
2.627711172296609115765958739218722735...
```

which is strictly below

```text
1 / 0.38055925
= 2.627711716375308181314736141612639818....
```

## Global Coverage

Price's partition has 172 mean bins.

- Bins 85 and 86 are replaced by the project center certificate.
- The other 170 bins were rerun at target `0.38055925`.
- Every reused bin passed.
- The largest reused denominator is
  `2.627538530873375790...`.
- The source gap from `0.025` to `0.025000000000000133` was covered by
  widening bin 94 to begin at `0.025`.
- Every mean-dependent right-hand side was recomputed after that widening.
- The complete project-generated 170-bin CSV, JSON, and log are retained and
  authenticated by the release audit.

The uniform denominator maximum over all 172 bins is therefore the project
center denominator, and it remains strictly below the target denominator.

## Strictness

The proof uses one finite maximum over all certified bins. Since that maximum
is strictly below `1/0.38055925`, every admissible overlap density has
supremum strictly greater than `0.38055925`. This avoids relying on a
pointwise strict inequality whose infimum might lose strictness.

## Adversarial Checks

The MPFI/C implementation passed:

- 18 malformed-certificate and proof-failure cases;
- Clang static analysis;
- AddressSanitizer;
- UndefinedBehaviorSanitizer;
- 128-bit and 256-bit verification runs.

The release launcher binds the evidence digest to the bytes consumed by C by
copying the already parsed and hashed payload into an unlinked open file
descriptor. The child process reads `/dev/fd/N`, so replacing the original
path cannot change the verified payload. The C traversal also enforces a hard
ten-million-cell budget.

The Python implementation includes parser mutation, target failure, artifact
hash, and released-certificate tests.

## Remaining Audit Boundary

- The exact value of `c_E` remains unknown.
- The noncentral result cites Price's publicly released certificate.
- The optimization is not trusted and is not claimed optimal.
- Independent external mathematical review is pending.
- A proof-assistant formalization of the new finite certificate is not yet
  available.
