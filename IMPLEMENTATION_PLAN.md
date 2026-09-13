# Implementation Plan: Asymmetric Claims-Centered Staffing and FEFx Fairness

**Architecture:** One-off ad hoc OpenCode delegation workflow
* **Theoretical Authority & Mathematical Brain:** Antigravity  
* **Executive Orchestrator:** GPT Luna in Codex, using the runbook below
* **Lead Implementer:** OpenCode  
**Target Repository:** `td` (`/Users/Shared/sv-ntlee/repos/td`)  
**Active Worktree:** `agy-math-review` (`/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review`)  
**Date:** September 13, 2026  

**Execution status:** Planning only. This document does not start implementation sessions.
The user must direct the orchestrator to begin the implementation job.

## Operating scope and precedence

This is a standalone job in this worktree. Do not use Beads, `bd`, `.beads/`,
Helios services, Helios configuration, Helios task tracking, or any in-flight
Helios setup. Do not inspect or import that setup. Do not write `STATE.md`,
existing `PLAN.md`, or Serena memories. The ad hoc ledger described below replaces
the normal task tracker for this job. These explicit user instructions override
repository instructions that route work through Beads or Claude orchestration.

Luna owns task dispatch, progress tracking, validation, and branch handoff.
OpenCode delegates own Python changes. Antigravity remains the mathematical
sign-off authority; a model review is not a substitute for that sign-off.
Luna must not silently resolve disputed mathematics or implement Python itself.

Only this implementation plan is being edited during planning. During execution,
each task receives an exact file allowlist. Preserve existing user changes.
Never edit `docs/MODEL_FULL.md`, `docs/foundations/`, the hub checkout, or unrelated
projects. Never merge or push `main`; never use `gh`.

Sections 2 through 6 retain the original proposed mathematics and deliverables.
They are subject to the explicit contract gate in section 7. Do not treat their
unverified mathematical claims as established guarantees.

---

## 1. Executive Summary & Architectural Roles

This document outlines the multi-phase engineering plan to implement the mathematical enhancements established in [`MATH_REVIEW.md`](MATH_REVIEW.md) and [`MATH_REVIEW.pdf`](MATH_REVIEW.pdf). The primary goal is to resolve the flat-curvature pathology of the Nash Social Welfare objective ($\max \sum \log g_{i,j}$), transition the fairness audit from invalidated unconstrained EF1 to **Feasible Envy-Freeness (FEFx)**, and eliminate spatial aggregation distortion via a terminal Stage 2 re-matching pass.

### Tri-Agent Operating Model

```
+-------------------------------------------------------------------------+
|                              ANTIGRAVITY                                |
|                 (Theoretical Brain & Verification Authority)            |
|  - Axiomatic formulations (FEFx, claims bankruptcy scaling, duals)      |
|  - Mathematical invariance proofs & convexity verification              |
|  - Invariant validation, certificate checks, and audit signing          |
+------------------------------------+------------------------------------+
                                     | Defines Math Specs & Guardrails
                                     v
+-------------------------------------------------------------------------+
|                             OPENAI CODEX                                |
|                        (Executive Orchestrator)                         |
|  - Task dependency graph execution and sprint pacing                    |
|  - Sub-process dispatching to OpenCode                                  |
|  - Worktree isolation, branch management, and CI gating                 |
+------------------------------------+------------------------------------+
                                     | Dispatches Implementation Tasks
                                     v
+-------------------------------------------------------------------------+
|                               OPENCODE                                  |
|                           (Lead Implementer)                            |
|  - Python code modification (`td/`, `tools/`, `tests/`)                 |
|  - Unit & regression test development (`pytest`)                        |
|  - Performance profiling, vectorization, and CLI plumbing               |
+-------------------------------------------------------------------------+
```

---

## 2. Core Mathematical Specifications

### Specification 1: Asymmetric Claims-Centered Reservation Utilities ($d_i$)

#### Theoretical Target
Restore steep curvature to the logarithmic objective $\log(g_i - d_i)$ to protect incumbent representatives from catastrophic book displacement while guaranteeing bargaining set feasibility.

#### Mathematical Formulation
For each representative $i \in R$, replace the legacy zero disagreement baseline ($d=0$) with:
$$d_i = \alpha_i S_i(Z) + d_{\text{floor}}$$
where:
1. **$S_i(Z)$** is rep $i$'s total historical book mass across the contested region:
   $$S_i(Z) = \sum_{z \in Z} \sum_{c} S_i(z, c)$$
2. **$\alpha_i \in (0, 1)$** is the **Proportional Bankruptcy Claims Factor**:
   $$\alpha_i = \min\left( 1.0, \; \frac{M(\text{Region})}{\sum_{k \in \text{overlap}} S_k(\text{Region})} \right) \cdot (1 - \epsilon)$$
   with $\epsilon = 0.05$ (headroom buffer).
3. **$d_{\text{floor}}$** is the common ambient floor:
   $$d_{\text{floor}} = \gamma \cdot \min_{j \in J} G_{0,j}$$
   with $\gamma = 0.60$, where $G_{0,j} = \sum_{z \in V_j} [c_2 T_z + c_{\text{free}} S_{\text{free}, z} + \lambda M_z]$.

#### Guardrail / Invariant
Before constructing the Hungarian cost matrix $C_{i,j} = -\log(g_{i,j} - d_i)$, assert:
$$g_{i,j} - d_i \ge 10^{-6} \cdot d_{\text{floor}} > 0 \quad \forall (i, j)$$
If any assignment violates this guard, smoothly clip to $\epsilon_{\text{floor}} = 10^{-6} d_{\text{floor}}$ with a logged warning.

---

### Specification 2: Feasible Envy-Freeness (FEFx) Audit Suite

#### Theoretical Target
Replace the classical $13 \times 13$ unconstrained EF1 matrix in [`tools/measure/audits.py`](file:///Users/Shared/sv-ntlee/repos/td/tools/measure/audits.py) with the three-way verdict matrix under Generalized Assignment Constraints (Barman et al., 2023).

#### Mathematical Formulation
For each pair of representatives $i, k \in R$, evaluate envy only if district $A_k$ is **feasible** for representative $i$ ($A_k \in \mathcal{F}_i$):
1. **Capacity Band Feasibility:** $L \le M(A_k) \le U$.
2. **Spatial / Geographic Feasibility:** District $A_k$ overlaps with rep $i$'s candidate territory (e.g., centroid distance $d(\text{home}_i, \text{center}(A_k)) \le D_{\max}$ or $S_i(A_k) > 0$).

#### Audit Output Matrix
For each active pair $(i, k)$:
* **Plain EF1:** $\exists z \in A_k \text{ s.t. } u_i(A_i) \ge u_i(A_k \setminus \{z\})$.
* **FEFx (w.r.t. $\mathcal{F}_i$):** If $A_k \in \mathcal{F}_i$, $\forall z \in A_k, \; u_i(A_i) \ge u_i(A_k \setminus \{z\})$.
* **Proportionality:** $u_i(A_i) \ge \frac{1}{k} u_i(Z)$.

---

### Specification 3: Terminal Stage 2 Re-Match Pass

#### Theoretical Target
Eliminate the spatial distortion caused by matching reps on continuous Level 0 state shares ($y_{s,j}$) rather than realized discrete ZIP code boundaries ($A_j$).

#### Mathematical Formulation
At the conclusion of Level 2 (post-cut and post-repair):
1. Compute the exact discrete gain matrix on realized ZIP sets:
   $$g_{i,j}^{\text{discrete}} = \sum_{z \in A_j} \sum_{c \in B_j} u_i(z, c)$$
2. Solve maximum-weight bipartite matching on centered utilities:
   $$\pi^*_{\text{terminal}} = \arg\max_{\pi} \sum_{i} \log\left( g_{i, \pi(i)}^{\text{discrete}} - d_i \right)$$
3. Compute and log the **Spatial Aggregation Distortion Metric**:
   $$\Delta W = \sum_{i} \log(g_{i, \pi^*_{\text{terminal}}(i)}) - \sum_{i} \log(g_{i, \pi_{\text{Level0}}(i)})$$

---

## 3. Phased Implementation Roadmap

```
+--------------------------------------------------------------------------+
| PHASE 1: Baseline Audit & Test Harness                                   |
| - OpenCode: Build FEFx audit module in `tools/measure/audits.py`         |
| - OpenCode: Create synthetic & real footprint unit tests                 |
| - Codex: Verify baseline tests pass with zero regressions                |
+------------------------------------+-------------------------------------+
                                     v
+--------------------------------------------------------------------------+
| PHASE 2: Asymmetric Claims Centering in Stage 2 Staffing                 |
| - OpenCode: Implement claims bankruptcy scaling in `td/stage2_state.py`  |
| - OpenCode: Add `--stage2-reservation` flag to CLI entrypoints           |
| - Antigravity: Verify non-emptiness proofs & numerical conditioning      |
| - Codex: Benchmark against baseline on CONUS instance                    |
+------------------------------------+-------------------------------------+
                                     v
+--------------------------------------------------------------------------+
| PHASE 3: Terminal Stage 2 Re-Match Pass                                  |
| - OpenCode: Implement `--stage2-rematch` in `tools/full_plan.py`         |
| - OpenCode: Log discrete gain delta $\Delta W$ and certificate updates   |
| - Codex: Run regression test suite on multi-split states (CA, TX, FL)    |
+------------------------------------+-------------------------------------+
                                     v
+--------------------------------------------------------------------------+
| PHASE 4: Verification, Benchmarking & Leadership Deliverables            |
| - OpenCode: Generate comparative 13x13 FEFx audit tables                 |
| - Antigravity: Review and sign off on mathematical certificates          |
| - Codex: Package final artifacts and executive report                    |
+--------------------------------------------------------------------------+
```

---

## 4. Detailed Task Breakdown

### Phase 1: Baseline Audit & Test Harness
* **Task 1.1 (OpenCode):** Create `tools/measure/audits.py` with `compute_envy_matrix(assignment, footprint, G)` implementing:
  * Plain EF1 check.
  * FEFx constraint filter (`is_feasible_for_agent(agent, district, bands)`).
  * Proportionality shortfall calculation ($u_i(A_i) - u_i(Z)/k$).
* **Task 1.2 (OpenCode):** Author unit test suite `tests/test_audits.py` validating FEFx pruning on a 2-agent toy instance and a 13-agent CONUS instance.
* **Task 1.3 (Codex):** Run `$TD_PY -m pytest tests/test_audits.py` and ensure 100% test pass.

### Phase 2: Asymmetric Claims Centering in Stage 2 Staffing
* **Task 2.1 (OpenCode):** In `td/stage2_state.py`, implement `compute_reservation_vector(instance, region, gamma=0.6, epsilon=0.05)`.
* **Task 2.2 (OpenCode):** Update `solve_staffing()` to accept `reservation_vector` and form costs:
  $$C_{i,j} = -\log\left( \max(g_{i,j} - d_i, \; \epsilon_{\text{floor}}) \right)$$
* **Task 2.3 (OpenCode):** Expose CLI argument `--stage2-reservation {none, uniform, claims}` across `tools/full_plan.py`.
* **Task 2.4 (Antigravity):** Verify that all $d_i$ satisfy the non-emptiness condition and that $C_{i,j}$ remains strictly convex.
* **Task 2.5 (Codex):** Run comparative solve on CONUS footprint and confirm no negative utility crashes.

### Phase 3: Terminal Stage 2 Re-Match Pass
* **Task 3.1 (OpenCode):** In `tools/full_plan.py`, hook an optional post-Level 2 pass `execute_terminal_rematch(realized_districts, reps)`.
* **Task 3.2 (OpenCode):** Update `staffing.json` with terminal assignment and record matching migration statistics (`reps_swapped`, `welfare_delta`).
* **Task 3.3 (Codex):** Execute full pipeline run with `--stage2-rematch` on worktree `agy-math-review`.

### Phase 4: Verification & Final Report
* **Task 4.1 (OpenCode):** Run `tools/measure/audits.py` on baseline vs. refined plans, emitting `fairness_audit_comparison.json`.
* **Task 4.2 (Antigravity):** Validate the FEFx matrix and verify that incumbent book retention increased significantly without violating capacity bands.
* **Task 4.3 (Codex):** Commit all changes to branch `worktree-agy-math-review` with descriptive, atomic commit messages.

---

## 5. Verification Invariants & Testing Guardrails

The orchestrator (Codex) and implementer (OpenCode) must enforce the following invariants at every step:

1. **Strict Non-Negative Headroom:** Pointwise headroom $M_z \ge \max(A_z + \theta B_z, B_z + \theta A_z)$ must hold across all processed ZIP codes.
2. **Capacity Band Integrity:** Final districts must strictly respect $[L_{B_j}, U_{B_j}]$ subject only to declared state-cap break allowances $a_s$.
3. **No Code Edits to Protected Files:** Do not modify `docs/MODEL_FULL.md` or files outside the agreed feature scope.
4. **Absolute Solver Feasibility Tolerance:** Linear and Hungarian programming solvers must maintain feasibility within $10^{-9}$ gain units.
5. **Scale Invariance Preservation:** Scaling instance opportunity by constant $\kappa$ must yield numerically identical matching assignments.

---

## 6. Definition of Done (DoD)

The implementation sprint will be complete when:
- [ ] `tests/test_audits.py` passes with full test coverage of EF1, FEFx, and Proportionality.
- [ ] `--stage2-reservation claims` successfully executes on the CONUS instance without numerical instabilities.
- [ ] Terminal re-match pass (`--stage2-rematch`) runs and reports exact $\Delta W$ distortion.
- [ ] FEFx audit confirms zero feasible envy across active territorial assignments.
- [ ] All code changes pass flake8/black formatting and standard repository lint checks.
- [ ] Antigravity conducts final mathematical review and signs off on verification certificates.

## 7. Mandatory contract gate before Python edits

Task C0 is read-only apart from its report. DeepSeek V4 Pro reads the relevant
sections of `MATH_REVIEW.md`, `AGY_REVIEW.md`, repository instructions, and current
interfaces. It writes a proposed contract with source locations and open questions.
Luna routes disputed points to Antigravity or the user. Qwen may supply a focused
second opinion. No dependent implementation starts with an unresolved contract.

The contract must settle:

1. The exact FEFx definition, including feasible subsets versus whole districts,
   removal quantifiers, zero-valued ZIPs, empty bundles, diagonal entries, and
   whether feasibility is tested before or after removal. A whole-district filter
   must not be presented as a theorem from the cited paper without verification.
   Plain EF1 must remain distinguishable from the feasibility-filtered audit.
2. Candidate eligibility, band selection, geographic rules and missing geography.
   Choose a documented rule, not the plan's unresolved example of distance OR book
   overlap. Use an explicit agent count for proportionality; `k` also names an agent
   in the original formulas. Mark ineligible comparisons as not applicable with a
   reason, not as successful fairness checks.
3. Reservation inputs and units, zero claims, zero ambient floor, empty regions,
   nonfinite inputs, parameter ranges, and uniform-mode semantics. Distinguish
   positive surplus on every edge from existence of a feasible complete matching.
   Log clipping does not itself establish bargaining feasibility. Define whether
   to reject, mask, clip, or adjust problematic edges, and expose that outcome.
4. The centered welfare optimized by rematching and the uncentered distortion
   metric printed in section 2. Define distinct output names if both are retained.
   Do not silently substitute one for the other or promise their deltas have the
   same sign. Compare assignments on the same realized ZIP gain matrix.
5. Eligible matching edges, held/released reps, rectangular or multi-rep cases,
   deterministic tie handling, and scale invariance with ties. Rematching must
   preserve fixed district membership, opportunity, and capacity compliance.
6. Numerical acceptance tolerances reconciled with the repository's existing
   certificate tolerances. Clarify what strict convexity refers to; a fixed
   Hungarian cost matrix is not a continuous strictly convex staffing program.
7. What evidence can establish zero feasible envy and improved retention. If the
   measured result fails either target, report that outcome and leave the target
   unmet. Do not weaken the audit, change thresholds, or claim that maximizing
   Nash welfare automatically supplies the requested fairness certificate.

Record exact APIs, types, array axes, units, defaults, output keys, and independently
computed toy expected answers. Write types before implementation. Keep the legacy
`none` and rematch-disabled behavior as the regression anchor. The contract is an
implementation prerequisite, not authorization to rewrite the protected model.

## 8. Model allocation and dependency ledger

Model assignments are a cost/risk starting point, not a benchmark claim that Qwen
is mathematically stronger than Pro. Review the first bounded patch before giving
any delegate a larger task. Use one OpenCode writer at a time in this worktree.
Luna can run independent read-only checks while a writer is active, but must not
launch competing file writers or validate a changing tree as a final result.

| ID | Original tasks | Model | Depends on | Deliverable and acceptance |
| --- | --- | --- | --- | --- |
| P0 | Preflight | Luna, shell only | Start authorization | Worktree, interpreter, tools, data availability, baseline commands and current quotas recorded |
| C0 | Contract gate | `opencode-go/deepseek-v4-pro` | P0 | Section 7 contract, toy expected answers, exact file/test map; unresolved points escalated |
| Q0 | Optional contract review | `opencode-go/qwen3.8-max` | C0 draft | Focused independent review when needed; does not confer Antigravity sign-off |
| A1 | 1.1 | `opencode-go/deepseek-v4-pro` | Accepted C0 | Audit predicates and typed results in `tools/measure/audits.py`; core examples pass |
| A2 | 1.2, 1.3 | `opencode-go/deepseek-v4.1-flash` | A1 | `tests/test_audits.py`, adversarial cases and fixture tests; Luna reruns tests |
| R1 | 2.1, 2.2 | `opencode-go/deepseek-v4-pro` | A2 | Reservation and centered matching core in `td/stage2_state.py`, numerical tests |
| R2 | 2.3 | `opencode/mimo-v2.5-free` | R1 | `tools/full_plan.py` CLI parsing, propagation and compatibility tests |
| G2 | 2.4, 2.5 | Antigravity and Luna | R2 | Mathematical gate and baseline/claims benchmark recorded |
| M1 | 3.1 | `opencode-go/deepseek-v4-pro` | G2 | Terminal discrete rematch and algorithm tests; fixed geography preserved |
| M2 | 3.2, 3.3 | `opencode-go/deepseek-v4.1-flash` | M1 | Output updates, migration statistics, integration tests; Luna runs pipeline |
| O1 | 4.1 | `opencode/mimo-v2.5-free` | M2 | Comparative JSON/tables using established audit results |
| Q1 | Independent final review | `opencode-go/qwen3.8-max` | O1 | Compact diff/contract review; defects returned to original owner |
| V1 | 4.2 and final validation | Antigravity and Luna | Q1, repairs | Full tests, CA/TX/FL and CONUS evidence, actual sign-off or explicit pending status |
| H1 | 4.3 | Luna | V1 | Atomic branch commits and push under active authority; final report |

Luna resolves exact additional test files at C0 before dispatch; the table is not
a wildcard permission to edit all of `td/`, `tools/`, or `tests/`. If an existing
target has a different name, record the mapping before editing. Tasks A1 and R1
include meaningful core tests; A2 is not the sole correctness gate. Do not dispatch
the numerical audit predicates to a free model merely because the code is short.

Free-model fallback is Go V4.1 Flash with the same scope. After two unsuccessful
repair turns on the same defect, stop that task and send its minimal reproducer,
diff and logs to Pro. An unresolved mathematical question goes back to C0, not
through repeated speculative patches. Keep the original session for related
repairs; use a new session for an independent review or materially new task.

## 9. Usage budgets and model availability

Snapshot checked September 13, 2026:
[Go usage limits](https://opencode.ai/docs/go/) and
[Zen pricing](https://opencode.ai/docs/zen/). Recheck these pages and the account
console at P0 and after a quota error. Published request counts are estimates based
on heavily cached, short-output traffic, not guaranteed implementation turns.

Token prices below are USD per million tokens. Allowances are usage value, not
additional subscription charges. Go lists five-hour limits at 20% of monthly
allowance and weekly limits at 50%.

| Model | Input | Output | Cache read | Cache write | Five-hour / week / month |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen 3.8 Max | 2.00 | 6.00 | 0.25 | 2.50 | $3 / $7.50 / $15 |
| V4 Pro off-peak | 0.66 | 1.98 | 0.022 | Not listed | $3 / $7.50 / $15 |
| V4 Pro peak | 1.32 | 3.96 | 0.044 | Not listed | $3 / $7.50 / $15 |
| V4.1 Flash off-peak | 0.15 | 0.60 | 0.003 | Not listed | $12 / $30 / $60 during promotion |
| V4.1 Flash peak | 0.30 | 1.20 | 0.006 | Not listed | $12 / $30 / $60 during promotion |
| Zen MiMo-V2.5 Free | Free | Free | Free | Not listed | No guaranteed capacity published |

Flash's 4x promotion ends September 20; its listed normal allowances are
$3 / $7.50 / $15. DeepSeek peak hours are Monday through Friday, 01:00-04:00 and
06:00-10:00 UTC. All other hours, including weekends, are off-peak. Use UTC when
scheduling. Prefer off-peak for Pro if it does not block useful progress.

For an illustrative batch totaling 1M uncached input, 10M cache-read, and 0.1M
output tokens, the table gives $5.10 for Qwen before any cache-write charge,
$1.078 for Pro off-peak, and $0.24 for Flash off-peak. These are arithmetic examples,
not task-cost forecasts. Record actual input/output/cache usage when available.

Zen also lists Big Pickle, Ling 3.0 Flash Fin Free, Nemotron 3 Ultra Free,
Nemotron 3.5 Lightning Free, and Muse Spark 1.3 Contributor Free. They are temporary
offerings. Use MiMo as the first bounded trial rather than rotating through every
model. Confirm availability and applicable data handling before sending project
context. Confidential instance rows must remain local; delegates get schemas,
synthetic examples, counts and aggregates under repository rules.

| Model | Internal five-hour target | Internal weekly target | Reserve purpose |
| --- | ---: | ---: | --- |
| Pro | $2 | $5 | Numerical/integration repairs |
| Qwen | $0.50 | $1.50 | Specific unresolved questions and final review |
| Flash | $2 | $5 | Compatible with normal post-promotion allowances |

These are soft planning ceilings, bounded by actual remaining account quota. Do
not assume model allowances are additive or independent: mixed-model accounting
must be checked in the console. Record console usage before and after a bounded
task, remaining five-hour/weekly/monthly allowance and displayed reset times.
If console access is unavailable, label quota remaining unknown and use small
tasks; do not invent remaining capacity from local token counts.

Do not silently enable Go's paid balance fallback, Zen auto-reload, or a paid Zen
model. A new conversation does not reset quota. On a limit error, record the exact
error/reset time and stop retrying until an eligible fallback or reset is available.
Proceed with independent local validation or a free supporting task when possible.
Do not downgrade an unresolved numerical implementation solely to keep it running.

Suggested work blocks, not promises that all work fits in one window:

- Block 1: P0, C0 and audits; R1 only if contract and budget permit.
- Block 2: reservations, integration and G2.
- Block 3: rematching, reporting and final review.
- Reserve weekly capacity for repairs. Two full $3 Pro windows leave only $1.50
  of its listed weekly allowance, even when each five-hour window has reset.

## 10. Luna's standalone execution runbook

### 10.1 Preflight and local task records

All commands use this exact worktree and pass through `rtk`. The shell startup in
this environment can reset the requested working directory, so include explicit
`cd` inside `rtk run` as shown. Do not rely on a previous command's directory.

```sh
rtk run 'cd /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review && pwd && git status --short --branch'
rtk run 'opencode --version && opencode run --help'
rtk run 'opencode models opencode-go'
rtk run 'opencode models opencode'
rtk run '/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 --version'
```

Record installed versions and verify the expected branch `worktree-agy-math-review`.
Inspect applicable TD instructions and only relevant code-map/model sections.
Do not consult existing workflow state to acquire unrelated work. Inspect task
targets with Serena overview/find_symbol and callers before signature changes;
use absolute worktree paths. If Serena or diagnostics are unavailable, record
the limitation and arrange an explicit fallback rather than claiming they ran.

At execution start, use `apply_patch` to create these job-local records, not during
the planning-only turn:

- `agy-job/ledger.json`: Luna-owned task ledger and quota observations.
- `agy-job/contract.md`: C0 report and accepted decisions.
- `agy-job/prompts/<task-id>.md`: exact task instructions written by Luna.
- `agy-job/reports/<task-id>.json`: delegate's structured result.
- `agy-job/logs/<task-id>-<attempt>.jsonl` and `.stderr.log`: raw runtime output.

No daemon, scheduler, shared queue, Beads database, or Helios dependency is needed.
Keep logs/transcripts and local quota records out of commits. Do not bulk-stage
`agy-job/`; select only approved, sanitized durable artifacts at handoff.

Each ledger task records `id`, `status`, `dependencies`, `model`, `files`,
`prompt_path`, `session_id`, `process_handle`, `attempt`, `started_at_utc`,
`last_progress_at_utc`, `log_paths`, `reported_cost`, `tests`, `review_verdict`,
`commit`, and `next_action`. Initialize unknown values as null, not guessed values.
Statuses are `pending`, `ready`, `running`, `reported`, `validating`, `accepted`,
`repair`, `blocked`, or `quota_wait`. Store blockers and console observations
separately with timestamps. `reported` never means `accepted`.

### 10.2 Task prompt template

Each prompt must be self-contained enough for a fresh OpenCode session:

```text
Task: <ID and one concrete deliverable>
Directory: /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review
Branch: worktree-agy-math-review
Mode: <read-only review OR implementation>
Read: <specific plan/contract sections and relevant source symbols>
Owned files: <exact relative paths, including report and tests>
Dependencies: <accepted task IDs and relevant contract decisions>
Types and behavior: <API, units, shapes, defaults, edge cases>
Acceptance: <independent expected results and exact test commands>
Scope: This is an ad hoc TD job. No Beads, Helios, STATE.md, PLAN.md or memories.
Do not edit protected model/foundations files or the hub checkout.
Use apply_patch for edits, Serena for code reading/callers, rtk for shell commands.
Keep confidential data rows out of model context and reports.
Do not delegate further, commit, push, install dependencies or change scope.
After edits, obtain file diagnostics and run the specified tests.
Report a scope or math blocker instead of inventing an answer.
Write the JSON report and return it as the final response.
```

Delegate report fields: `task_id`, `status` (`complete`, `blocked`, or `failed`),
`summary`, `files_changed`, `tests` (command, exit code, result), `artifacts`,
`math_questions`, `followups`, `learned`, and `missing_context`. Luna records the
actual session ID from OpenCode output; the delegate must not invent it.

### 10.3 Start and resume OpenCode

User-required permission mode: launch every OpenCode task and resumed session
with `opencode run --yolo`, the user-specified short flag for dangerously skipping
permissions. Keep this flag in review, implementation, and repair invocations.
The task's file allowlist and read-only constraints still apply.

The earlier local OpenCode 1.18.30 help listed `--auto` rather than `--yolo`.
P0 must verify that the execution installation accepts `--yolo`. If it rejects
the flag, report the version mismatch; do not silently substitute `--auto` or
start a permission-prompting session. The commands below express the requested
mode, not a claim that `--yolo` was tested during this plan update.

`--pure` disables external plugins; it does not promise to disable all inherited
configuration, agents or MCP servers. P0 must establish that the invocation uses
only TD-local resources and needed tools. If an unrelated integration is inherited,
isolate the job using documented OpenCode configuration before dispatch. Do not
read or modify Helios setup to do so and do not launch a known cross-project agent.

Example after Luna creates C0's prompt, report directory, and log directory:

```sh
rtk run 'cd /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review && opencode run --yolo --pure --model opencode-go/deepseek-v4-pro --format json --title agy-C0 --file agy-job/prompts/C0.md -- "Execute the attached C0 task. Write agy-job/contract.md and agy-job/reports/C0.json. Follow its read-only scope." > agy-job/logs/C0-01.jsonl 2> agy-job/logs/C0-01.stderr.log'
```

Run this via Codex's command tool with a short initial yield, for example 1000 ms.
Keep the returned process/session handle and poll that same handle. Do not detach
it with `&` and lose exit status. The shell process handle and OpenCode `ses_...`
conversation ID are different identifiers; record both.

For A2 and M2 replace the model with `opencode-go/deepseek-v4.1-flash`; for R2 and
O1 use `opencode/mimo-v2.5-free`; for Q0/Q1 use `opencode-go/qwen3.8-max`.
Use the relevant prompt, title and unique attempt log paths for every invocation.
Do not attach the entire repository or real instance data. Leave provider-specific
`--variant` unset unless its supported values have been verified for that model.

To request a repair, first write the exact failure and reproducer into a repair
prompt using `apply_patch`, then resume the recorded conversation. Replace
`ses_REPLACE_WITH_RECORDED_ID` below with the actual ID, never use it literally:

```sh
rtk run 'cd /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review && opencode run --yolo --pure --model opencode-go/deepseek-v4-pro --session ses_REPLACE_WITH_RECORDED_ID --format json --file agy-job/prompts/C0-repair-01.md -- "Address only the attached review findings and update the task report." > agy-job/logs/C0-02.jsonl 2> agy-job/logs/C0-02.stderr.log'
```

Use `--session` rather than `--continue`, which could select another job's latest
conversation. Never resume the same OpenCode conversation concurrently. Starting
a different model for an independent review should use a new session with a compact
contract/diff attachment rather than the implementer's entire conversation.

### 10.4 Monitor status and recover

While a command is running, use the command tool's `write_stdin` with the recorded
process handle, empty input and a wait no longer than 60 seconds. Read just recent
log lines. Send the user a concise progress update at least once per minute during
active work. Useful commands, executed only for this job's records:

```sh
rtk run 'cd /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review && tail -n 12 agy-job/logs/C0-01.jsonl && tail -n 12 agy-job/logs/C0-01.stderr.log'
rtk run 'cd /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review && opencode session list --format json --max-count 20'
rtk run 'cd /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review && opencode stats --days 1 --models --project ""'
```

Extract the OpenCode session ID from the actual JSON events. If absent, identify
it by exact task title, worktree and start time in session metadata. Do not inspect
other projects' conversations. The installed CLI has no `session status` command;
a list entry is not proof that work is running or successful. Running state comes
from the process handle and new events. Completion needs process exit status,
delegate report, inspected diff, and independent validation.

Local `stats` is a diagnostic, not authoritative Go quota accounting. Inspect the
actual event schema before extracting cost/token fields. Missing costs mean unknown,
not zero. Preserve cache counters when available and compare with console usage.

If no progress events arrive for five minutes, inspect the task's stderr, process
state and active tool operation. Long solver execution may be legitimate. Check
whether it is waiting for credentials, permissions, a rate-limit reset or input.
Do not launch a duplicate writer. If intervention is needed, terminate only the
recorded task process and its verified children, preserve partial changes and logs,
then resume or escalate with the failure evidence. Never use broad `pkill` commands.

If Luna restarts or its context is compacted, read this plan, the local ledger,
latest report and concise diff first. Verify whether recorded processes remain
alive before any new launch. Preserve accepted tasks and resume only the next
ready task or interrupted attempt. Do not reset status from scratch.

### 10.5 Validate, accept, and hand off

Luna follows this loop until the job completes or a concrete external blocker
prevents progress:

1. Choose a pending task whose dependencies are accepted and whose model has budget.
2. Write its exact prompt and record the baseline diff, then mark it running.
3. Launch once, capture both IDs, monitor events and retain the exit status.
4. Read the report and mark it reported. Inspect all changed paths, not only those
   the delegate lists. Stop and resolve out-of-scope edits without discarding user work.
5. Run independent validation after the writer exits; mark validating. On failure,
   dispatch a bounded repair with the exact evidence. On success, mark accepted.
6. Update quota observations and the next action before dispatching another task.

Use the hub interpreter from this worktree. Do not install or change the frozen
environment. P0 verifies the actual runner and lint configuration; do not assume
the original plan's pytest/flake8/black commands are all installed or configured.
For an available pytest audit module, the focused command is:

```sh
rtk run 'cd /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review && rtk test /Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -m pytest tests/test_audits.py'
```

For the repository's custom full runner, preserve its complete output and process
exit code. Repository instructions specifically forbid `rtk test` around this
runner because it can hide FAIL lines:

```sh
rtk run 'cd /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review && /Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -u tests/run_all.py > agy-job/logs/full-tests.log 2>&1'
rtk rg -n --max 80 'FAIL|ERROR|SKIP|fail|summary' /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/agy-job/logs/full-tests.log
```

Check both runner exit status and its final summary; a zero exit status alone is
insufficient. Log a missing test dependency or unavailable data as blocked or
skipped with a reason. A synthetic 13-agent test does not replace a real CONUS run.

P0/C0 must determine the existing full-pipeline command and data paths from TD's
recipes and CLI help. Record the exact baseline, claims and rematch invocations
before launching expensive solves. Pin instance, opportunity scale, seed, solver
settings, gazetteer vintage and district count across comparisons. Write results
into separate new run directories. Keep old artifacts intact. Benchmark output
must include capacity results, raw and centered welfare where contracted, clipping
or infeasibility counts, incumbent retention, and applicable/inapplicable fairness
pair counts. CA/TX/FL regressions must check realized split-state districts.

At H1, stage explicit reviewed paths, use atomic `agy-math-review: <summary>`
commits on `worktree-agy-math-review`, and push only that branch when authorized
by the active user instructions. Never stage logs, confidential data, unrelated
changes or local quota records. Never merge. An unavailable mathematical sign-off
is a reported blocker to full completion, not permission to fabricate approval.

Final handoff JSON fields: `status`, `tasks_accepted`, `tasks_blocked`,
`files_changed`, `validation`, `benchmark_artifacts`, `math_signoff`, `commits`,
`push_status`, `usage_observations`, `followups`, `learned`, and `missing_context`.
Distinguish implementation complete from all original mathematical targets met.
