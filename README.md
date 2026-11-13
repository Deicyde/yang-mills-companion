# Does the Yang–Mills manuscript follow the Lean?

*Unreviewed machine audit. AI agents produced every verdict; no mathematician has checked any of it.*

This companion is not affiliated with or reviewed by Scott Armstrong, the humanise-yang-mills project,
OpenAI or the yang-mills-group. Corrections are welcome as issues.

**Scope.** [M] is the manuscript `main.pdf` of
[scottnarmstrong/yang-mills-informalization](https://github.com/scottnarmstrong/yang-mills-informalization),
241 pages. [L] is the Lean construction
[yang-mills-group/OpenAI-YM-20261028](https://github.com/yang-mills-group/OpenAI-YM-20261028), the revision
[M] cites. For each of [M]'s 206 numbered statements and 252 numbered displays, its 355 unnumbered displays
outside proofs and the 1,607 steps of its 129 proofs, agents found the declarations, or the lines of [L], that
state it and compared the two. They read [L]'s source at the pin; they did
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
**65 of the 206 statements and 87 of the 252 displays have an exact counterpart** in [L]. **33 items are
confirmed findings**: [M] prints something [L] does not prove as stated. None is a principal statement, and
none is a typo.

Items by status (statements / displays); the relation is that of the item's key links, subject [M], object [L]:

| status | relation | statements | displays |
|---|---|---:|---:|
| exact, definition-match | `exactMatch` | 65 | 87 |
| close, definition-close | `closeMatch` | 43 | 86 |
| stronger ([L] more general) | `broadMatch` | 13 | 14 |
| parts | `hasPart` | 57 | 29 |
| inlined (inside a proof of [L]) | `relatedMatch` | 0 | 17 |
| not formalized, not needed | `noMatch` | 3 | 2 |
| **weaker** (finding) | `narrowMatch` | 17 | 4 |
| **differs** (finding) | `relatedMatch` | 0 | 5 |
| **no-match** (finding) | `noMatch` | 3 | 4 |
| unclear (contested or unsettled) | none | 5 | 4 |

Every numbered item has a completed verdict; none is "Not yet judged". Their 1,733 annotations hold one record
per item for its key declarations together, carrying the item's relation, and one per other link: 152 `exactMatch`,
129 `closeMatch`, 27 `broadMatch`, 86 `hasPart`, 21 `narrowMatch`, 1,240 `relatedMatch` and 12 `noMatch`, and
66 records of unclear items with no relation.
The 355 unnumbered displays and 1,607 proof steps have one record each, a step in its item's folder with the
lines of [L] that carry it. 288 of them, where mapper and verifier disagreed only between exactMatch and a weaker
formalized relation or only on the declarations, keep the weaker or the mapper's verdict by rule, unjudged; their
provenance says so.

### Confirmed findings

Each survived two skeptics, each told to refute it and each reading [M]'s LaTeX and [L]'s source. Each
line quotes what [M] prints and names the closest declarations of [L].

- **Lemma 10.2** (`a box stencil $\Sigma_d=[-\varrho_d,\varrho_d]^4\cap\Z^4$`): the stencil is the box [-ρ_d,ρ_d]⁴ ∩ ℤ⁴; [L]'s `localSection` is a choice from `Bid.Learns`, and `sound` gives only a stencil containing 0 and stable under signed permutations (the box appears only inside `Work.G06.answer`'s proof).
- **Lemma 11.6** (`vanishes to order at least $j$ at every nonzero alias`): the averaging symbol vanishes to order ≥ j at every nonzero alias; [L] states only that it vanishes there (`Flight.vanishing_box`).
- **Lemma 11.7** (`The stationary Gaussian integral, including the inherited loop action and Haar density, has field-dependent factor $\mathrm e^{-\mathsf T(v)}$`): the field-dependent factor e^{-T(v)} of the stationary Gaussian integral, and positivity of Q(v) near zero; [L] has J_ax = |det Ds| (`treasury`), J_ax > 0 (`toll_pos`), XR = I (`carries`) and det(R,I)² = 1 (`commandment`), but positivity of Q only at v = 0 (`tested_diag`) and of det Q(v) near zero (`hessian_pos`).
- **Lemma 11.8** (`\|D^r(A_\mu^{-1})\|_{\rm dual\to primal}\le Q_r(C_j^{\rm ins}),\qquad \|\mu^2D^r(A_\mu^{-1})\|^{\rm bl}\le Q_r(C_j^{\rm ins})`): the bounds on D^r(A_μ^{-1}) by Q_r(C^ins) for r = 1, 2 and the μ²-scaled block bounds; [L] states the trace bound on the flat P_μ³ (`thin_doubled`), bounds on P_μ through two insertions (`pebbles_frozen`) and only the r = 0 dual-to-primal bound on the joint inverse (`completion_choice`).
- **Eq (11.6)** (`\le x+\mu^2\,.`): the upper inequality x + μ²(μ²/(x+μ²))⁹ ≤ x + μ²; [L] states only the lower one (`YM.Stationary.terrain_min`).
- **Lemma 11.9** (`Gauge-annihilating mixed functionals satisfy $b_1\mathsf Gb_2=b_{1,\rm ax}\mathsf Q^{-1}b_{2,\rm ax}$.`): the identity b₁Gb₂ = b_{1,ax}Q^{-1}b_{2,ax}; [L] states the momentum orders (`greyson`), the C₃, C₄ bounds (`setWest`) and the D⁴S_stat bound with 1/4! normalization (`exchangeYield`), but only the abstract matrix identity `radiant` for the pairing.
- **Lemma 11.10** (`Y^{\rm con}_{ii}(te_1)=O(t^3)`): Y^con_ii(te₁) = O(t³); [L] states α_b = 0 (`drift_tip`), momentum order two (`tax_ray`), analyticity of c (`star_analytic`) and b(0) = 0 (`star_low`), and the O(t³) bound only as a step inside `drift_tip`'s proof.
- **Lemma 11.13** (`\prod_{i\ {\rm seed}}a_i\le e^{-\kappa'_B\beta t^2|A|}`): the seed-envelope bound ∏a_i ≤ e^{-κ'βt²|A|} and the value majorant with (1+s_A)^d e^{-κ'βt²|A|} for A_c ≠ ∅; [L] has the molecule majorant (`Daisy.Herd`), the warning bound E^r and a packet bound exp((C·bill⁵ − βμ·fiery²)·shares) (`Invoices`), and Haar and tag factorization (`Pond.marched`, `Tags.uses`).
- **Lemma 12.3** (`The same bounds hold at $w_{J_m}^\prime>w_{J_m}^{\rm path}>0$ with $A_{J_m}^\prime\ge A_{J_m}^{\rm path}>0$ replacing $A_{J_m}^{\rm path}$, uniformly in $N$.`): the bounds at a larger width w' > w^path with A' ≥ A^path; [L] states them at the stage width (`Kin.Planned`) and moves only to smaller widths (`Installed`, `Scheduling.narrower`).
- **Lemma 13.4** (`For $W_0$ satisfying $(2B+1)^4\sup_x\sum_{a:x\in Z_a}v_a\le\eta$, $\mathcal R(W_0)\le v_0e^{\eta n_0}$.`): the rooted bound R(W₀) ≤ v₀e^{ηn₀} under (2B+1)⁴ sup_x Σ_{a: x∈Z_a} v_a ≤ η for this step's connected expansion, with R(W₀) = max{R_reg(W₀), e^{r_jβ'_u t²_{m+1}} R_for(W₀)}; `Boulevard.lays` states the identity and the β^{-7/16} and forced bounds but has no extra factor W₀, and [L] states the rooted bound only for abstract overlap gases (`Copse.flights`) and, in the alternative construction of III.13, for one distinguished leaf (`Willow.heights`)
- **Eq (13.4)** (`\text{stationary-action remainder}&P_j\beta'_u g^3\le P'_j\mathfrak b^{-1/2}\\ \text{centered determinant remainder}&P_j(t_{m+1}+g)\le P'_j\mathfrak b^{-1/2}\\ \text{Gaussian-density and stationarity residuals}&P_j\mathfrak b^{c_j^{\rm res}}e^{-c_j^{\rm tail}B}\\ \text{Haar-Jacobian remainder}&P_j(t_{m+1}+g)^2`): the row-by-row majorants, e.g. P_jβ'_u g³ for the stationary-action remainder, P_j(t_{m+1}+g) for the determinant remainder and P_j(t_{m+1}+g)² for the Haar-Jacobian remainder; [L] proves only the assembled molecule majorant with one rate −1/2 prefactor (`Daisy.timing`) and prices the cubic, quartic and loop path terms separately (`Song.stanzaReady`)
- **Lemma 13.5** (`\mathcal E(R)\le \omega_{j,\ell_m}^{\rm inh}(\refbeta_m)\epsilon_{m+1}^{\rm reg}, \end{equation*} where $V_j$ is fixed before the ratio and $\omega_{j,\ell}^{\rm inh}$ has scale rate $-1/2$. The identity $T_i=P_i+R_i$ and the corresponding weighted comparisons hold on the entire input curve.`): the remainder bound E(R) ≤ ω^{inh}_{j,ℓ_m}ε^{reg}_{m+1} at all supports, and the weighted comparisons on the entire input curve; [L]'s `Brim.pressings` gives the principal bound (C'/L)ε^{reg} at all supports but the remainder's sup bound only where coverNumber ≤ B (`Brim.Houses`), at each input separately
- **Lemma 13.7** (`a continuous scalar $\tau_u$`): continuity of the scalar τ_u; [L]'s `Use.Offering` (proved by `Rain.glazing` with τ = `stanzaFee`) gives the identity, the bounds, the regularity, equivariance and weighted continuity of the families (`Collection.Compared`), but leaves τ an arbitrary function ℝ → ℝ
- **Eq (13.21)** (`\mathcal E_m\le\epsilon_m^{\rm reg}/1024,\qquad \mathcal K_m\le\epsilon_m^{\rm for}/1024`): the factor 1/1024 in ℰ_m ≤ ε_m^reg/1024 and 𝒦_m ≤ ε_m^for/1024; [L]'s `Deployment.recloses` bounds ℰ_m by `Calendar.allowance` = ε_m^reg and 𝒦_m by `Calendar.forcedAllowance` = ε_m^for and by e^{−g_j (M^cut_{m+1})²}, with no factor 1/1024
- **Lemma 13.17** (`there are continuous symmetric multilinear maps $T_k:X^k\to Y$`): symmetry of the T_k, and the bound 2C(4e/(rR))^k for 1 < R < 2; [L]'s `Rebar.recovery` (needing 1 ≤ R/2) composed with `Amp.Often.gardenL`, `Amp.Often.course`, `Amp.Often.party` and `Amp.stage` gives the continuous multilinear T_k with ‖T_k‖ ≤ 2C(4e/(rR))^k, the series and the completion only for R ≥ 2, and no declaration states symmetry
- **Lemma 13.18** (`have convergent real multilinear expansions on the ball of radius $1/4$. Their degree-$k$ coefficients, $k\ge1$, have norms at most $g_*$, $\varrho_m$ and $g_*$`): convergent multilinear expansions on the ball of radius 1/4 with degree-k coefficient norms ≤ g_*, ϱ_m, g_*; [L] has holomorphic extensions on the ball of radius 2⁻¹⁷ with sup and Lipschitz bound 2⁻²⁰ (corrections: `worth`) and no coefficient bounds (`Spire.Fitted.zesty`, `Oriel.conquest`), the sum bound in its own normalization (`Camp.levy`) and cutoff compatibility (`Roads.Unum.commute`)
- **Eq (13.29)** (`\mathcal T_m^a(K+\lambda(H-K)) =\mathcal T_m^a(K)+\lambda(\mathcal T_m^a(H)-\mathcal T_m^a(K))`): affineness of the normalized kernel-coefficient map T_m^a in the incoming kernel; [L] compares cutoffs through the Lipschitz bound of `Camp.Seal`, with truncation error soft^{k−m} (`Camp.mist`), and has no kernel-coefficient map
- **Eq (13.31)** (`u_m&=(2z_m)^{-1}\left[b_m^{-1} \left(\mathfrak e-\sum_{i<m}\widehat{\mathcal D}_{N,i}(u_{i+1},W_{i+1})\right)-\chi_m u_m^2\right]`): the third line, with factor (2z_m)^{-1} and term χ_m u_m² from β_m = β̂_m(χ_m x_m)²; [L]'s `Camp.Cart.veil` is z_i = pulse_i⁻¹(b − ∑_{j<i} tally_j), linear in the coupling coordinate, on complex points rather than series (the first two lines match `Camp.Cart.play`)
- **Eq (14.6)** (`2A_{j,d}(2B_i+1)^4(1+B_i)^4 \widehat\beta_i^{q_d}\zeta_{d,i}\le\eta_i/2`): 2A_{j,d}(2B_i+1)⁴(1+B_i)⁴β̂_i^{q_d}ζ_{d,i} ≤ η_i/2 with the attachment threshold η_i; [L]'s `Legato.Bandage.creek` bounds e^{σ+2}·cameras_d·β̂^{q_d}ζ_{d,i} by `stub` = β̂^{-1/2}/4 without the B-factor, and `Legato.Bandage.Steam` carries (2B+1)⁴(stain + Q·siteFactor(B)·stub) ≤ 3 separately; neither implies the other.
- **Eq (14.10)** (`\alpha_t^n\mathcal C_j^{h_t(b)+v_t+2}\mathcal E_t^{\rm G}\le1`): α_t^n 𝒞_j^{h_t(b)+v_t+2} ℰ_t^G ≤ 1, and the band β̂_i ∈ [β̂_t/2, β̂_t] on all of k_t ≤ i ≤ t; [L]'s `Peak.Charge` has Q^cmp ≤ log ℳ_t/(16n) (`Ship.Allocated.charge`), the band only on [t−h_t−v_t, t−h_t] (`Peak.Charge.assured`), and the billing conditions `Perch.Tally` in place of the first requirement; neither implies the other.
- **Lemma 14.1** (`All requirements~\ref{it:E-columns}--\ref{it:E-birth} and~\eqref{eq:E-marker-scales} can be met with`): that the requirements, among them ϖ_{J_i} = o(s_i), can be met; [L] has the calendar (`Wait.engine`), log ℓ_m/s_m → 0 (`Fits.mesh`), ℓ_m → ∞ (`Bridge.reach`), the o(s) bound on (a_m/a_{k(m)})⁴q_{k(m)} (`Stock.consumes`) and the comparison windows (`Paid.run`, `Ship.honoured`), but no bound ϖ_{J_i} = o(s_i).
- **Eq (14.36)** (`=T^{n_1^{\rm sl}}(T^lX-XT^l)T^{n_2^{\rm sl}-l}`): the operator identity T^{n₁+l}XT^{n₂−l} − T^{n₁}XT^{n₂} = T^{n₁}(T^lX − XT^l)T^{n₂−l} and its split into two (1 − T^l) terms; [L] bounds the displacement by another route, a Cauchy derivative estimate in the complex exponent (`Holder.finite_lip`, used by `Extraction.Difference.primitive`)
- **Eq (14.45)** (`\mathcal C_j^{h_t(b)+v_t+2} \le\mathcal M^{(b+6)/j^2}B_t^{10/j^2} \le\mathcal M^{1/64}`): 𝒞_j^{h_t(b)+v_t+2} ≤ ℳ^{(b+6)/j²}B_t^{10/j²} ≤ ℳ^{1/64}, a bound over all h_t+v_t+2 steps; [L]'s `Perch.Tally.growth` bounds the growth over the v_t steps only, (α+1)^{v_t} ≤ ℳ^{1/4} (`Perch.on_time`); neither implies the other.
- **Eq (14.58)** (`\sum_{i=m}^{h-1}2^{-(i-m)}\delta_i(N,N')`): the cross-cutoff bound d_m(N,N′) ≤ 2^{1−(h−m)} + Σ_{i=m}^{h−1} 2^{−(i−m)}δ_i(N,N′); [L] has only the term 2·(1/2)^{d′}, between W i n and a reference sequence flowed d′ levels down from a remote level (private `Gear.shawls`), with no δ_i, and gets the Cauchy property from it qualitatively (`Gear.voyages`).
- **Eq (15.1)** (`\partial_{\boldsymbol l}f_{P(k),v}\longrightarrow \partial_{\boldsymbol l}S_n(v;\cdot) \quad\text{locally uniformly on }\Conf{n}`): ∂_l f_{P(k),v} → ∂_l S_n(v;·) locally uniformly on Conf_n; [L] has only convergence of values on compact subsets of the generic set (`Extraction.RawLimits`, `Extraction.Order.VolumePoints`), and C^∞ on Conf_n only for a replacement table T equal to S at generic points (`Org.Arrives.serves`, `Org.Cleaner`).
- **Lemma 15.1** (`\partial_{\boldsymbol l}f_{P(k),v}\longrightarrow \partial_{\boldsymbol l}S_n(v;\cdot) \quad\text{locally uniformly on }\Conf{n}`): ∂_l f_{P(k),v} → ∂_l S_n(v;·) locally uniformly on Conf_n; [L] has the extraction, value convergence on compact generic sets, the ordered convergence of smears and persistence under refinement (`Extraction.first_surface`, `Extraction.RawLimits`, `Extraction.copy_down`), and C^∞ only for a replacement table T equal to S at generic points (`Org.Arrives.serves`).
- **Eq (15.3)** (`\sup_{p\ge p_0}\sup_{x\in K'}|\partial_{\boldsymbol l}f_{p,v}(x)| \le B(v,\boldsymbol l,r)`): sup_{p≥p₀} sup_{x∈K′} |∂_l f_{p,v}(x)| ≤ B(v,l,r) for l ≠ 0; [L] bounds only values: lattice values uniformly in p on compact subsets of Conf_n (`Extraction.Bound`) and the volume tables at single generic points (private `Extraction.extendsBound`), and takes equicontinuity from the Lipschitz input (`Extraction.volume_oscillates`).
- **Lemma 16.3** (`For every $d\ge4$, finitely many sums`): for every d ≥ 4, finitely many sums separate B_d; [L]'s `Maxwell.Free.erasing` states only that all Ward sums separate B_d for d beyond an unspecified threshold (`Org.erases`: ∃ n, ∀ d ≥ n), and finite selection only for an abstract finite-dimensional family (`Work.A07.finite_rows`).
- **Lemma 16.11** (`The tensor is centered, nonzero`): the averaged tensor T is centered and nonzero; [L]'s `Work.A15.answer` (`Bid.A15`) gives only Conserved, Tensorial and StressLaws for the average, and centering and nonvanishing (`StressFlux.Centers`) are proved only for a different stress chosen from a kernel (`StressFlux.exists_stress`, `StressFlux.stress_weak`).
- **Lemma 16.12** (`Along the single stable sequence of Proposition~\ref{prop:SC}, for every fixed $d,a,K$,`): both operator-norm limits along the single stable sequence of Proposition SC, for every fixed d, a, K; [L] has the derivative limit and the unnormalized charge limit (X.ξ_k)⁻¹·transport → κ·L^Max only for scalings with a `Track` beyond thresholds depending on d (`Bid.A04`, `Bid.A05`), and the normalized rotation limit only for transports chosen separately for each d (`Org.Commission`, `Spin.Tilt`).
- **Eq (17.4)** (`\left|\int f\,d\nu_d^{UV}\right|^2\le\int g_1\,d\nu_d^U\int g_2\,d\nu_d^V`): |∫ f dν_d^{UV}|² ≤ ∫ g₁ dν_d^U ∫ g₂ dν_d^V; [L]'s `Outer.cross_le` gives only ‖∫ f dν^{UV}‖ ≤ t∫a dν^U + (∫b dν^V)/t for every t > 0, whose optimum 2(∫a ∫b)^{1/2} is the squared bound with constant 4.
- **Lemma 17.7** (`for every finite Schwartz test sequence~$F$ in the field-word algebra`): W^ξ(F*F) ≥ 0 for every finite Schwartz test sequence F in the field-word algebra; [L] proves positivity only on Sentences, words whose letters each carry one test in Test4 (`Boundary.Fields.sees`, `Boundary.Surface.wordsPositive`), not for joint Schwartz tests.
- **Lemma 18.3** (`\sup_{x\in K}\left|S_{n_{\rm ar}}(U_i(\boldsymbol d)\boldsymbol A^{(i)};r_ix^{(i)})-\maxwellcorr_{n_{\rm ar}}(\boldsymbol A;x)\right|\to0`): sup_{x∈K} |S(U_i(d)A^{(i)}; r_i x^{(i)}) − S^Max(A;x)| → 0 at the lattice-rounded points x^{(i)}, the translation-shell flux limit, the phase-uniform case n_ar = 2, and exact compatibility of the frames with inclusions; [L] has the subsequence, frames preserving conjugation, signed permutations and units, levels → ∞ and (18.1) (`MergeProof.East.pays_sky`, `MergeProof.East.StarPath`, `Trace.Over.gang`), and the jet comparison for convergent inputs only at the unrounded points r_k x (`Next.UVStress.travels_jet`).

Eqs (13.4), (14.36) and (14.58) are displays inside proofs that [L] proves by another route. Eq (11.6)'s missing
inequality is elementary.

<!-- coverage: written by scripts/coverage.py -->
## Coverage

Each statement, display and proof step has one class; "formalized" is 1-to-1 + Faithful. The
definitions, the 1-to-1 list, every deviation and the absences: [`docs/coverage.md`](docs/coverage.md).

| | 1-to-1 | Faithful | Partial | Deviates | Absent | Unjudged | Formalized |
|---|---|---|---|---|---|---|---|
| Statements | 65/206 (32%) | 56/206 (27%) | 57/206 (28%) | 20/206 (10%) | 3/206 (1%) | 5/206 (2%) | **121/206 (59%)** |
| Displays | 290/607 (48%) | 215/607 (35%) | 59/607 (10%) | 36/607 (6%) | 3/607 (0%) | 4/607 (1%) | **505/607 (83%)** |
| Steps | 602/1607 (37%) | 502/1607 (31%) | 214/1607 (13%) | 261/1607 (16%) | 28/1607 (2%) | 0/1607 (0%) | **1104/1607 (69%)** |

Unjudged steps and unnumbered displays are those whose mapper and verifier disagreed and no judge reached: 0 of 1607 steps and 0 of 355 displays. Of the judged steps, 1104/1607 (69%) are formalized; of the judged unnumbered displays, 318/355 (90%).

| Section | Statements formalized | Displays formalized | Steps formalized | Steps absent | Deviations |
|---|---|---|---|---|---|
| 1 | — | 10/10 (100%) | — | — | 0/10 (0%) |
| 2 | 3/3 (100%) | 7/9 (78%) | — | — | 1/12 (8%) |
| 3 | 10/10 (100%) | 35/37 (95%) | — | — | 0/47 (0%) |
| 4 | 9/11 (82%) | 12/14 (86%) | — | — | 1/25 (4%) |
| 5 | 5/5 (100%) | 11/13 (85%) | — | — | 0/18 (0%) |
| 6 | 13/15 (87%) | 13/13 (100%) | — | — | 0/28 (0%) |
| 7 | 6/7 (86%) | 14/14 (100%) | — | — | 0/21 (0%) |
| 8 | 8/11 (73%) | 7/7 (100%) | 8/10 (80%) | 0/10 (0%) | 0/28 (0%) |
| 9 | — | 3/3 (100%) | — | — | 0/3 (0%) |
| 10 | 1/4 (25%) | 16/18 (89%) | 51/61 (84%) | 0/61 (0%) | 7/83 (8%) |
| 11 | 4/13 (31%) | 58/67 (87%) | 168/253 (66%) | 5/253 (2%) | 59/333 (18%) |
| 12 | 4/10 (40%) | 24/27 (89%) | 90/105 (86%) | 0/105 (0%) | 5/142 (4%) |
| 13 | 7/21 (33%) | 54/69 (78%) | 149/272 (55%) | 5/272 (2%) | 85/362 (23%) |
| 14 | 20/33 (61%) | 77/103 (75%) | 184/285 (65%) | 5/285 (2%) | 58/421 (14%) |
| 15 | 1/5 (20%) | 14/20 (70%) | 31/41 (76%) | 0/41 (0%) | 9/66 (14%) |
| 16 | 5/12 (42%) | 39/47 (83%) | 138/172 (80%) | 0/172 (0%) | 22/231 (10%) |
| 17 | 1/10 (10%) | 31/38 (82%) | 120/131 (92%) | 0/131 (0%) | 9/179 (5%) |
| 18 | 10/13 (77%) | 33/42 (79%) | 66/131 (50%) | 13/131 (10%) | 33/186 (18%) |
| 19 | 14/23 (61%) | 47/56 (84%) | 99/146 (68%) | 0/146 (0%) | 28/225 (12%) |

By statement share: most formalized Sections 2 (3/3), 3 (10/10), 5 (5/5), 100% each; least Section 17, 1/10 (10%). By step share (sections with proofs): most formalized Section 17, 120/131 (92%); least Section 18, 66/131 (50%).

<!-- /coverage -->

## What was checked and what was not

Checked: every item's region against `main.pdf` itself (a rebuild matching its layout on all 241 pages); every
declaration named against an index built from [L]'s source at the pin; each verdict by a mapper and an
independent verifier, a judge when they disagreed, and two skeptics for each claimed finding; the items an independent
review disputed, re-judged and, where a finding changed, re-checked by two new skeptics; the annotations by
the Literature Links scan and `check_generated.py` (also in CI).

Not checked: whether [L]'s declarations are proved (it was not built, Comparator was not run, axioms were not
inspected); whether hypotheses carried as structure fields are discharged for the actual construction, except
where an agent traced it; non-findings, which no skeptic tested; the 18 claimed findings that were not confirmed
(8 contested, left without a relation; 5 refuted; 5 withdrawn on re-reading [L] after an independent review). No person reviewed any verdict.

## License

Apache-2.0 (`LICENSE`, `NOTICE`). Quoted Lean and manuscript text belong to their authors under Apache-2.0.
