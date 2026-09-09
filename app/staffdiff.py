"""Before-and-after arithmetic on the incumbent layout and a staffing.

Everything here is ratios: `weight` (a zip's share of the whole channel book) and
`book_share` (a rep's share of it) are the two currency the app already reports in
`reps.json`, so nothing computed here needs the instance itself. Standard library only, no
streamlit, pandas or plotly, so this stays testable from the solver venv.

`rows` are the dicts `app.mapfig.load_rows` returns: `zip, state, x, y, opportunity,
district, rep`. `staffing` is a loaded `staffing.json` (`tools/staff.py`): `assignment` maps
a district to its rep, `unstaffed_districts` lists the rest.
"""
from __future__ import annotations


def _weight_by_zip(reps: dict) -> dict[str, float]:
    return {z: info.get("weight", 0.0) for z, info in reps.get("zips", {}).items()}


def per_rep(reps: dict, rows: list[dict], staffing: dict) -> list[dict]:
    """One row per rep in `reps["reps"]` order: `rep`, `before` (`book_share`), `after` (the
    weight of the zips the table's `rep` column now credits them with), `districts` (the
    ones they are assigned, in table order), `change` (`after - before`)."""
    weight = _weight_by_zip(reps)
    before = reps.get("book_share", {})
    assignment = staffing.get("assignment", {})

    after: dict[str, float] = {}
    districts: dict[str, list[str]] = {}
    for row in rows:
        rep = row.get("rep")
        if not rep:
            continue
        after[rep] = after.get(rep, 0.0) + weight.get(row.get("zip", ""), 0.0)
        dists = districts.setdefault(rep, [])
        d = row.get("district")
        if d and d not in dists:
            dists.append(d)

    out = []
    for rep in reps.get("reps", []):
        b = before.get(rep, 0.0)
        a = after.get(rep, 0.0)
        out.append(dict(rep=rep, before=b, after=a,
                        districts=districts.get(rep, []), change=a - b))
    return out


def summary(reps: dict, rows: list[dict], staffing: dict) -> dict:
    """Whole-map counts: how many reps hold territory before and after, how much book sits
    on contested ground before and after, and how much book is free before versus unstaffed
    after."""
    weight = _weight_by_zip(reps)
    zips = reps.get("zips", {})
    assignment = staffing.get("assignment", {})
    unstaffed = set(staffing.get("unstaffed_districts", []))

    top_reps_before = {info["top"] for info in zips.values() if info.get("top")}
    contested_before = sum(w for z, w in weight.items() if zips.get(z, {}).get("n", 0) >= 2)
    free_before = reps.get("free_share", 0.0)

    reps_after = {row["rep"] for row in rows if row.get("rep")}

    n_by_district: dict[str, set] = {}
    for row in rows:
        d = row.get("district")
        if not d:
            continue
        n_by_district.setdefault(d, set()).add(row.get("rep") or "")

    contested_after = 0.0
    unstaffed_after = 0.0
    for row in rows:
        d = row.get("district")
        w = weight.get(row.get("zip", ""), 0.0)
        if d and d in unstaffed:
            unstaffed_after += w
        elif d and len(n_by_district.get(d, set())) >= 2:
            contested_after += w

    return dict(
        reps_with_territory_before=len(top_reps_before),
        reps_with_territory_after=len(reps_after),
        contested_weight_before=contested_before,
        contested_weight_after=contested_after,
        free_weight_before=free_before,
        unstaffed_weight_after=unstaffed_after,
    )


def district_view(reps: dict, rows: list[dict], staffing: dict, district: str) -> dict:
    """One district's book, before (by today's `top` rep) and after (by the table's `rep`
    column), each normalised to the district's own weight so both sides sum to 1."""
    weight = _weight_by_zip(reps)
    zips = reps.get("zips", {})
    in_district = [row for row in rows if row.get("district") == district]
    total = sum(weight.get(row.get("zip", ""), 0.0) for row in in_district)

    before: dict[str, float] = {}
    contested = 0.0
    untapped = 0.0
    for row in in_district:
        z = row.get("zip", "")
        w = weight.get(z, 0.0)
        info = zips.get(z, {})
        n = info.get("n", 0)
        top = info.get("top") or ""
        if n >= 2:
            contested += w
        elif top:
            before[top] = before.get(top, 0.0) + w
        else:
            untapped += w

    after: dict[str, float] = {}
    for row in in_district:
        rep = row.get("rep") or ""
        w = weight.get(row.get("zip", ""), 0.0)
        after[rep] = after.get(rep, 0.0) + w

    def _norm(d: dict[str, float]) -> dict[str, float]:
        return {k: (v / total if total > 0 else 0.0) for k, v in d.items()}

    return dict(
        before=dict(_norm(before), contested=(contested / total if total > 0 else 0.0),
                   untapped=(untapped / total if total > 0 else 0.0)),
        after=_norm(after),
    )
