# References

What td relies on each paper for: one row per claim that rests on a paper (S29–S31). The paper
records live in the global registry, `/Users/Shared/sv-ntlee/kb/references.bib`, and the quoted
passages live in the kb page named in each row. Statuses:
- `verified`: the passage was read at its source, quoted in the kb, and checked for a retraction on
  OpenAlex;
- `claimed`: not yet read;
- `withdrawn`: kept with the reason, so the paper is not cited again for that claim.

| claim | key and result | kb page | status | note |
|---|---|---|---|---|
| `MODEL.md` §5 Claim 3, *Origin*: at a vertex of the unrelated-machines assignment LP, the positive job–machine graph is a pseudoforest, the structure Lemma 3a adapts | `lenstra1990` Thm 1 (Rounding Theorem), proof | `assignment-lp-rounding` | verified | Read 2026-09-29 in the authors' CWI Report OS-R8714 (1987), `ir.cwi.nl/pub/6083/6083D.pdf`, not the journal text, whose theorem numbering was not checked. OpenAlex W2102201348: not retracted (checked 2026-09-29). |
| `MODEL.md` §5 Claim 3, *Origin*: LST rounding is one-sided: each machine gets at most one job beyond its fractional share, so its load is at most d_i + t | `lenstra1990` Thm 1 (Rounding Theorem) | `assignment-lp-rounding` | verified | Same reading and check as the row above. |
| none in `MODEL.md`. The archived staffing work cited it as the basis for "books enter at stage 2 only" | `fotakis2014` (DOI 10.1145/2665005) | — | withdrawn | Withdrawn 2026-09-05 (★8 at the tag `archive/pre-support-2026-09`) as an over-read. The paper characterises deterministic strategyproof mechanisms for K-facility location, where agents report their locations. For K ≥ 3 on the line it shows that no deterministic anonymous strategyproof mechanism has a bounded approximation ratio (OpenAlex abstract, read 2026-09-29). The staffing formulation meets neither hypothesis: it is rep-indexed, not anonymous, and books are not reported locations (`docs/foundations/DOMAIN_economic-theory.md` §2.7(a) at the tag). Do not cite it for that claim again. OpenAlex W1536918079: not retracted (checked 2026-09-29). |
| `problem/SPLITS.md` §2.1, §4.2: minimising split units and minimising splits are distinct problems; a hierarchy is solved by pinning the first optimum | `shahmizad2026` §1, §3 | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). Read in the Optimization Online preprint (2025-10); page numbers are the preprint's. |
| `problem/SPLITS.md` §4.2, SU3: weak split duality (minimum cuts ≥ K − maximum number of clusters), tight on 140 instances, gap unbounded; the Sketch MIP's shares capped by touch binaries; the obvious bound | `shahmizad2025` Thm 1, Prop. 1, Prop. 2, §4.2 eqs. 3a–3f, §5.1–5.2 | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). Read in the NSF PAR accepted manuscript. |
| `problem/SPLITS.md` §4.2: a lexicographic court rule and the maximum-cluster rule give different optima | `carter2020` Def. 1, Table 1 | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). Read in arXiv 1908.11801 v1. |
| `problem/SPLITS.md` §4.2: at a basic solution of the transportation relaxation at most p − 1 units are split and the split adjacency is a forest; balance as a side constraint | `kalcsics2005` §4.1, §5.1–5.2 | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). Read in ITWM Bericht 71; page numbers are the report's, not TOP's. |
| `problem/SPLITS.md` §4.2: commercial territory design minimises a diameter-type dispersion with balance bands | `riosmercado2009` §3, eq. 1 | `territory-design` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). Read in the author's copy. |
| `problem/SPLITS.md` §4.2: packing with fragmentation has an optimal solution fragmenting each item at most once; the compact model's LP bound is trivial | `casazza2016` Thm 2.1, §2.2 | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). Read in the Optimization Online 2015 preprint. |
| `problem/SPLITS.md` §4.2: ε-constraints order secondary districting objectives | `swamy2022` §4.2 | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). Read in the Optimization Online 2019 preprint. |
| `problem/SPLITS.md` §4.2: no classical compactness measure tracks human judgement reliably; statute language on thin strips | `kaufman2021` p. 546, fn. 3 | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). |
| `problem/SPLITS.md` §4.2: cut edges reasonably agree with the eyeball test | `validibuchanan2022` abstract | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). |
| `problem/SPLITS.md` §4.2: Polsby–Popper is sensitive to necks and spurs | `duchin2018` §3.1 | `districting-models` | verified | Read 2026-10-04 (#90); quote in the `LEARNED[kb]` lines on #90, kb filing pending on m2. OpenAlex: not retracted (checked 2026-10-04). Read in arXiv 1808.05860 v2. |

Candidates that `MODEL.md` does not cite, so they are not in the registry through td:
- `shmoystardos1993`, already in the registry. `MODEL.md` proves its two-sided bound directly and
  does not need this one-sided result.
- `lauravisingh2011`: Lemma 3a proves the forest property directly.
- `borgwardt2019` and `brieden2017`: `MODEL.md` §7 proves the power-diagram remark from LP
  duality.
