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

Candidates that `MODEL.md` does not cite, so they are not in the registry through td:
- `shmoystardos1993`, already in the registry. `MODEL.md` proves its two-sided bound directly and
  does not need this one-sided result.
- `lauravisingh2011`: Lemma 3a proves the forest property directly.
- `borgwardt2019` and `brieden2017`: `MODEL.md` §7 proves the power-diagram remark from LP
  duality.
