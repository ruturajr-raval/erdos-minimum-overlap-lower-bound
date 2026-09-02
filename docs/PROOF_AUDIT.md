# Proof Audit

Status: complete for the retained Station certificate. No project-original
theorem is asserted here.

## Reduction Checked

For a balanced partition, replace each integer by an interval of width `1/N`. The
continuous overlap is a triangular interpolation of the discrete difference counts.
Because the triangular weights over adjacent integer differences sum to at most one, its
supremum is at most the largest discrete count divided by `N`. Thus a continuous lower
bound transfers in the required direction to the discrete liminf.

## Analytic Identities Checked

- The overlap density has mass one and mean in `[-1, 1]`.
- If its mean is `mu`, its second moment is `2/3 + mu^2/2`.
- Centered transforms satisfy `H + G = 2 sinc(xi)`.
- The stated cosine lower and upper bounds, sine bound, and
  `C_xi + alpha S_xi` bound follow from `|H|, |G| <= 1` and completing the square.
- With nonnegative dual multipliers, `q = 1 + sum lambda_j (B_j - phi_j)` satisfies
  `integral p q >= 1`, so an upper bound on `integral max(q, 0)` yields a lower bound on
  the overlap supremum.

## Strictness Checked

The prior-art certificate uses finitely many mean bins. If each certified denominator is
strictly below `1/C`, their finite maximum is also strictly below `1/C`, giving a uniform
bound strictly above `C`. This avoids the invalid inference that an infimum of merely
pointwise strict inequalities must remain strict.

## Checker Hardening

The hash-pinned Station C executable is preserved unchanged, but direct invocation is not
treated as a safe general-purpose API: it can parse `NaN` and report a passing budget.
The project wrapper now validates the authenticated row before execution and rejects
non-finite, duplicate, negative-budget, or over-budget output fields.

The prior-art Arb checker was replayed with `rhs_inflate = 1e-14`, but its command-line
interface permits a negative inflation. That is a checker defect outside this repository.
The provenance replay checks only the repository-reported comparison target
`c_E > 0.38055470`; the longer inverse decimal is retained as a non-strict
diagnostic benchmark. This is not an independent validation of the claim.

## Open Gates

- Extend the separate verifier from the licensed Station certificate language to any
  future project certificate language.
- Produce a project candidate strictly above the repository-reported comparison target.
- Obtain external review before any project-original theorem announcement.
