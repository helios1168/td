"""tests/test_docs_owners.py -- the doc-ownership allowlist and the STATE.md / unit-file shape
it depends on (`.claude/doc-owners.txt`, read by `~/.claude/hooks/td-doc-owners.sh` and here).

(a) every docs/**/*.md outside docs/foundations/ matches at least one allowlist line;
(b) every non-glob line names an existing file, every glob line matches at least one file;
(c) no allowlist line points under docs/foundations/ (read-only, never listed);
(d) STATE.md has exactly the H2 headings ## Now, ## Next, ## Facts in that order, ## Now is at
    most 1024 bytes, ## Next has at most 7 rows;
(e) every docs/units/*.md has a Status: open|done|dropped line in its first 5 lines and the
    three headings ## Model, ## Verify, ## Code verify.

Matching uses `fnmatch`, which gives `*` the same "matches anything, including `/`" behaviour as
the hook's shell `case` patterns -- both are plain string globs with no path-segment awareness.
"""
from __future__ import annotations

import fnmatch
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ALLOWLIST = os.path.join(ROOT, ".claude", "doc-owners.txt")
STATE = os.path.join(ROOT, "STATE.md")
UNITS_DIR = os.path.join(ROOT, "docs", "units")


def _allowlist_lines():
    with open(ALLOWLIST, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    return [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def _all_docs_md(exclude_foundations=True):
    """Every docs/**/*.md path relative to ROOT, forward-slashed."""
    out = []
    docs_root = os.path.join(ROOT, "docs")
    for dirpath, dirnames, filenames in os.walk(docs_root):
        rel_dir = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
        if exclude_foundations and (rel_dir == "docs/foundations" or rel_dir.startswith("docs/foundations/")):
            continue
        for f in filenames:
            if f.endswith(".md"):
                out.append(f"{rel_dir}/{f}" if rel_dir != "docs" else f"docs/{f}")
    return out


def test_every_non_foundations_doc_is_allowlisted():
    patterns = _allowlist_lines()
    docs = _all_docs_md(exclude_foundations=True)
    assert docs, "expected at least one docs/**/*.md file outside docs/foundations/"
    orphans = [d for d in docs if not any(fnmatch.fnmatch(d, pat) for pat in patterns)]
    assert not orphans, f"orphaned docs not in {ALLOWLIST}: {orphans}"


def test_allowlist_lines_resolve_to_real_files():
    patterns = _allowlist_lines()
    docs = _all_docs_md(exclude_foundations=False)
    for pat in patterns:
        if any(ch in pat for ch in "*?["):
            matches = [d for d in docs if fnmatch.fnmatch(d, pat)]
            assert matches, f"glob line {pat!r} in {ALLOWLIST} matches no file"
        else:
            assert os.path.isfile(os.path.join(ROOT, pat)), f"line {pat!r} in {ALLOWLIST} names no file"


def test_allowlist_never_points_under_foundations():
    for pat in _allowlist_lines():
        assert "docs/foundations/" not in pat and pat != "docs/foundations", (
            f"{ALLOWLIST} lists {pat!r} under the read-only docs/foundations/"
        )


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _h2_sections(text):
    """[(heading, [body_lines]), ...] for every top-level '## ' heading, in file order."""
    sections = []
    cur_heading = None
    cur_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur_heading is not None:
                sections.append((cur_heading, cur_lines))
            cur_heading = line[3:].strip()
            cur_lines = []
        elif cur_heading is not None:
            cur_lines.append(line)
    if cur_heading is not None:
        sections.append((cur_heading, cur_lines))
    return sections


def test_state_md_heading_order_and_now_cap():
    text = _read(STATE)
    sections = _h2_sections(text)
    headings = [h for h, _ in sections]
    assert headings == ["Now", "Next", "Facts"], f"STATE.md H2 headings are {headings}, expected [Now, Next, Facts]"
    now_lines = dict(sections)["Now"]
    now_text = ("\n".join(now_lines) + "\n") if now_lines else ""
    now_bytes = len(now_text.encode("utf-8"))
    assert now_bytes <= 1024, f"STATE.md ## Now is {now_bytes} bytes, over the 1024 byte cap"


def test_state_md_next_row_cap():
    text = _read(STATE)
    next_lines = dict(_h2_sections(text))["Next"]
    table_rows = [ln for ln in next_lines if ln.startswith("|") and not set(ln.strip("| \t")) <= set("-:")]
    if len(table_rows) >= 2:
        rows = table_rows[1:]  # drop the header row; the separator row was already excluded
    else:
        rows = [ln for ln in next_lines if ln.startswith("- ")]
    assert len(rows) <= 7, f"STATE.md ## Next has {len(rows)} rows, over the 7 row cap"


def test_unit_files_have_status_and_verifier_headings():
    unit_files = sorted(f for f in os.listdir(UNITS_DIR) if f.endswith(".md"))
    assert unit_files, "expected at least one docs/units/*.md file"
    for f in unit_files:
        path = os.path.join(UNITS_DIR, f)
        lines = _read(path).splitlines()
        head = lines[:5]
        assert any(
            ln.startswith("Status: open") or ln.startswith("Status: done") or ln.startswith("Status: dropped")
            for ln in head
        ), f"{f}: no 'Status: open|done|dropped' line in the first 5 lines"
        for heading in ("## Model", "## Verify", "## Code verify"):
            assert heading in lines, f"{f}: missing {heading!r} heading"
