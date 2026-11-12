# Does the Yang–Mills manuscript follow the Lean?

*Unreviewed machine audit. AI agents produced every verdict; no mathematician has checked any of it.*

This companion is not affiliated with or reviewed by Scott Armstrong, the humanise-yang-mills project,
OpenAI or the yang-mills-group. Corrections are welcome as issues.

**Scope.** [M] is the manuscript `main.pdf` of
[scottnarmstrong/yang-mills-informalization](https://github.com/scottnarmstrong/yang-mills-informalization),
241 pages. [L] is the Lean construction
[yang-mills-group/OpenAI-YM-20261028](https://github.com/yang-mills-group/OpenAI-YM-20261028), the revision
[M] cites. For each of [M]'s 206 numbered statements and 252 numbered displays, agents found the
declarations of [L] that state it and compared the two statements. They read [L]'s source at the pin; they did
not build it or run Comparator. Each annotation records how its link was made and that no person reviewed it.

## Pins

| | |
|---|---|
| [M] (SRC_PIN) | `1a47ac9007f80d37832291cc12d578874ff6bef9` |
| `main.pdf` sha256 | `29d9743c7429fbc2b412975b9082adecb51163b0a8ee5f4c7d855ca55a9bde13` (2,107,222 bytes, 241 pages) |
| [L] (LEAN_PIN) | `3456e5e75cf8d4cd558955a5c7638fba2d68f464` |

## Viewing it

```sh
cd manuscript
python3 pdf-overlay/tools/serve.py --build
```

then open <http://127.0.0.1:8000/pdf-overlay/viewer/index.html>. `serve.py` fetches `main.pdf` from
`raw.githubusercontent.com` at SRC_PIN, checks its sha256 and serves it on loopback only; the PDF is not in
this repository. The annotations (`manuscript/annotations/`, [Literature Links](https://github.com/mathlib-initiative/literature-links)
1.0.1) can be read without the viewer.

## The answer

For its principal results [M] follows [L]; elsewhere it does not always. All 17 principal statements (Theorems A
and B and the 15 of Table 1) have a counterpart: 5 exact, 6 close, 2 proved more generally in [L], 4 by parts.
**65 of the 206 statements and 87 of the 252 displays have an exact counterpart** in [L]. **38 items are
confirmed findings**: [M] prints something [L] does not prove as stated. None is a principal statement, and
none is a typo.

Items by status (statements / displays); the relation is that of the item's key links, subject [M], object [L]:

| status | relation | statements | displays |
|---|---|---:|---:|
| exact, definition-match | `exactMatch` | 65 | 87 |
| close, definition-close | `closeMatch` | 43 | 85 |
| stronger ([L] more general) | `broadMatch` | 13 | 14 |
| parts | `hasPart` | 56 | 24 |
| inlined (inside a proof of [L]) | `relatedMatch` | 0 | 18 |
| not formalized, not needed | `noMatch` | 3 | 3 |
| **weaker** (finding) | `narrowMatch` | 12 | 4 |
| **differs** (finding) | `relatedMatch` | 0 | 5 |
| **no-match** (finding) | `noMatch` | 9 | 8 |
| unclear (contested or unsettled) | none | 5 | 4 |

Every item has a completed verdict; none is "Not yet judged". The 2,345 annotation files hold 336 `exactMatch`,
253 `closeMatch`, 50 `broadMatch`, 345 `hasPart`, 43 `narrowMatch`, 1,200 `relatedMatch` and 23 `noMatch` links,
and 95 links of unclear items with no relation.

### Confirmed findings

Each survived two skeptics, each told to refute it and each reading [M]'s LaTeX and [L]'s source. The
annotations name the declarations compared.

- **Lemma 10.2**: the stencil is the box [-ρ_d,ρ_d]^4 ∩ Z^4; [L]'s `localSection` is a choice whose stencil is not stated to be a box.
- **Lemma 11.6**: the averaging symbol vanishes to order ≥ j at nonzero aliases; [L] states only that it vanishes there.
- **Lemma 11.7**: the field-dependent factor e^{-T(v)} of the stationary Gaussian integral, and positivity of Q(v); [L] has neither.
- **Lemma 11.8**: the trace-norm and block-norm bounds on P_μ, D^r P_μ and D^r(A_μ^{-1}); not stated in [L].
- **Eq (11.6)**: the upper inequality; [L] states only the lower one (`YM.Stationary.terrain_min`).
- **Lemma 11.9**: the momentum orders of V_2, V_3, V_4 and the bounds on C_3, C_4 and D^4 S_stat; not stated in [L].
- **Lemma 11.10**: momentum order two, analyticity and the O(t^3) form; [L] proves only α_b = 0 (`YM.Stationary.drift_tip`).
- **Lemma 11.13**: the seed-envelope bound and the value majorant with (1+s_A)^d e^{-κ'βt²|A|}; not stated in [L].
- **Lemma 12.3**: the bounds at a larger width w' > w^path; [L] moves only to smaller widths.
- **Lemma 13.4**: the rooted bound R(W_0) ≤ v_0 e^{η n_0}; not stated in [L].
- **Eq (13.4)**: the row-by-row remainder table; [L] proves the majorant as a whole.
- **Lemma 13.5**: the remainder bound at all supports and continuity on the input curve; [L] bounds it only where coverNumber ≤ B.
- **Lemma 13.7**: continuity of τ_u; [L] leaves τ_u an arbitrary function.
- **Eq (13.21)**: the factor 1/1024 on E_m and K_m; [L] has the allowances without it.
- **Lemma 13.17**: the lemma from the stencil hypothesis, and symmetry of the T_k; [L] states neither.
- **Lemma 13.18**: expansions on the ball of radius 1/4 with coefficient bounds; [L] works on radius 2^-17 without them.
- **Eq (13.29)**: affineness of T_m^a in the incoming kernel; not stated in [L].
- **Eq (13.31)**: the third line's factor (2z_m)^{-1} and term χ_m u_m²; [L]'s `Camp.Cart.veil` is linear in β.
- **Lemma 13.19**: the history comparison for two endpoints; [L] compares two points at one endpoint.
- **Eq (14.6)**: [L]'s `Legato.Bandage.creek` bounds by another quantity, without [M]'s factor; neither implies the other.
- **Eq (14.10)**: [L]'s `Peak.Charge` replaces the first requirement by billing conditions; neither implies the other.
- **Lemma 14.1**: log l_m → ∞, log l_m/s_m → 0, ϖ = o(s) and the comparison intervals for the constructed calendar; not stated in [L].
- **Eq (14.14)**: the δ/b_* term for two endpoints; [L] contracts at one endpoint only.
- **Eq (14.36)**: the operator identity; [L] proves the bound by another route (`Holder.finite_lip`).
- **Eq (14.45)**: the bound M^{1/64} over all steps; [L] bounds the v_t steps by M^{1/4}; neither implies the other.
- **Eq (14.52)**: the bounds on e_j − J_h e_j; [L] never forms J_h.
- **Eq (14.53)**: the level-product bound with decay in s_h − s_m; not stated in [L].
- **Eq (14.58)**: the quantitative bound on d_m; [L] proceeds by a qualitative induction (`Gear.spends`).
- **Eq (15.1)**: smoothness of S_n and convergence of derivatives; [L] proves value-level convergence and smoothness of another table.
- **Lemma 15.1**: the same two claims as Eq (15.1); missing from [L].
- **Eq (15.3)**: the derivative bounds for l ≠ 0; [L] bounds only values.
- **Lemma 16.3**: finitely many Ward sums separate B_d; [L] states it for all sums.
- **Lemma 16.11**: centering and nonvanishing of the averaged tensor; not stated in [L].
- **Lemma 16.12**: one sequence along which both limits hold for every d, a, K; [L] chooses per d.
- **Eq (17.4)**: the sharp constant; [L]'s `YM.Outer.cross_le` gives the squared bound only with constant 4.
- **Lemma 17.7**: positivity for joint Schwartz tests; [L] proves it only for Sentences.
- **Lemma 18.3**: the comparison at lattice-rounded points, the flux limit and the phase-uniform case; not stated in [L].
- **Eq (19.2)**: 1 + 2C_l ≤ ℓ_l^{1/40}; not stated in [L].

Eqs (13.4), (14.36) and (14.58) are displays inside proofs that [L] proves by another route. Eq (11.6)'s missing
inequality is elementary.

## What was checked and what was not

Checked: every item's region against `main.pdf` itself (a rebuild matching its layout on all 241 pages); every
declaration named against an index built from [L]'s source at the pin; each verdict by a mapper and an
independent verifier, a judge when they disagreed, and two skeptics for each claimed finding; the annotations by
the Literature Links scan and `check_generated.py` (also in CI).

Not checked: whether [L]'s declarations are proved (it was not built, Comparator was not run, axioms were not
inspected); whether hypotheses carried as structure fields are discharged for the actual construction, except
where an agent traced it; non-findings, which no skeptic tested; the 13 claimed findings that were not confirmed
(8 contested, left without a relation; 5 refuted). No person reviewed any verdict.

## License

Apache-2.0 (`LICENSE`, `NOTICE`). Quoted Lean and manuscript text belong to their authors under Apache-2.0.
