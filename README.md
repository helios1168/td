# td — support-master territory design

td plans sales districts for each planning channel of a national channel. Each channel's
(ZIP, fine channel) opportunity is divided into K_c districts whose drawn masses sit inside a
band. The pipeline has three parts:

1. a support-based master MILP that plans districts per channel;
2. a ZIP realizer that turns planned unit shares into whole-ZIP borders;
3. an audited `(ZIP, fine channel) → district` ledger.

The plan is [#52](https://github.com/helios1168/td/issues/52), with milestones M0–M5. As of
2026-09-28 the repository is at its M0 clean slate: the package `td/` does not exist yet.
Everything earlier is in the tag `archive/pre-support-2026-09`, including the Nash staffing
model, the app, the notes and the old support pipeline.

## Layout

- `export/`: the exporter, run on the work machine (`export/README.md`).
- `docs/problem/`: the problem ledger and unknowns. `docs/lenses/`: lens and council output.
  `docs/memory/`: facts and decisions.
- `tests/`: `run_all.py` runs every `test_*.py`.

`docs/CODE_MAP.md` lists every file and its role.

## Setup

One environment, `.venv`, from `requirements.txt`:

```bash
uv venv .venv && uv pip install --python .venv/bin/python3 -r requirements.txt
.venv/bin/python3 tests/run_all.py
```

The confidential extract, `instance_descaled*.json.gz`, is gitignored and never committed
(`docs/memory/workflow/confidential-data.md`).
