# Economic-theory verdicts already reached on td (do not re-derive)

Latest domain run 2026-09-03 (A1 charter, joint coverage optimisation).

**Retired for good.** Monte-Carlo Shapley over 111 players (`littlechild1973` plus additivity
gives a closed form, O(#zips·n log n)); the Bondareva-Shapley balancedness LP as the first core
test (`deng1999`'s integrality check replaces it); "is the EG bound decorative?" (no: U1-cert
P3, at most k-1 splits); "is ρ = 0?" (yes, and ρ does not enter stage 2: `mem:model/u2-stab`).

**Ruled out on hypothesis checks.** Shapley and Shubik 1971 assignment game (needs transferable
utility; the frame forbids transfers). Shapley and Scarf 1974 / TTC (needs initial endowments;
greenfield). Kelso and Crawford 1982 gross substitutes (preferences are aligned, vertical, not
horizontal).

**★8** (`fotakis2014` and Gibbard-Satterthwaite, both withdrawn) is AGENTS.md trap 17. The
misreporting exposure (the inflation incentive of the unselected reps, A1-Q4's non-obvious
manipulability) remains live.

**What the measured numbers implied.** δ and ε are two knobs, not one; the EG-V gap's
extremiser is over an infeasible set, and `EG^bal` replaces it; the premium roster gap is the
whole collective claim of the unselected reps; few contested zips make coverage near-modular and
maximally gameable; the Nash-tie margin means the optimal roster is non-unique.

**The invariance split.** Under `G = (R_{>0})^R` acting on reported books: at fixed roster the
EG argmax, prices and band duals are invariant (the value shifts by `Σ log γ_i`, Nash 1950
scale invariance); `max_S EG_S` is not invariant, so selection is manipulable. Caveat: the
programme's `u_i` is affine, not homogeneous, in `S_i` because of the `c2·T_z` coupling, so the
theorem does not apply as-is to the model as built. Check the coupling before quoting.

**Hand-offs that stay open.** Regional bias in `M` (A4 / U5) to econometrics: highest value,
it would invalidate every certificate silently. Displacement metric to optimization (U4-disp).
Tier-2 noise floor (U6) to econometrics. No `DOMAIN_econometrics.md` exists (★7).

Related: `mem:domain/economic-theory-conventions`, `mem:refs/econ-theory-matching`.

Source: `.claude/agent-memory/domain-lens/domain-economic-theory-td.md` (2026-09-03).
