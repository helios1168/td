"""
test_zip50_anchor.py -- the byte-identity regression guard (PLAN.md U0a).

Runs `code/mkfig_zip50.py` (the project's numeric anchor, ~2 min) and checks

  1. its stdout, modulo wall-clock tokens, equals `anchors/mkfig_zip50.stdout.txt`;
  2. the three regenerated PNGs hash to `anchors/figures.sha256`
     (`zip50_distributions.png` is d-independent and never regenerated, but its hash
     is recorded too so an accidental overwrite is caught).

Any change to `code/territory.py`, `code/districting.py`, `code/synth.py`,
`code/zip50.py`, `code/mkfig_zip50.py` or `battery/code/mapviz.py` must keep this green.

    TD_SLOW=1 .venv/bin/python3 battery/code/tests/run_all.py -k zip50
    .venv/bin/python3 battery/code/tests/test_zip50_anchor.py            # run directly
    .venv/bin/python3 battery/code/tests/test_zip50_anchor.py --update   # re-anchor (deliberate!)
"""
from __future__ import annotations
import hashlib, os, re, subprocess, sys

SLOW = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ANCHORS = os.path.join(HERE, "anchors")
STDOUT_ANCHOR = os.path.join(ANCHORS, "mkfig_zip50.stdout.txt")
SHA_ANCHOR = os.path.join(ANCHORS, "figures.sha256")
FIGURES = ["nash_solution.png", "zip50_nash_milp.png", "nash_contestability.png",
           "zip50_distributions.png"]

_TIME_TOKENS = [
    (re.compile(r"time=\d+(\.\d+)?s"), "time=<T>"),
    (re.compile(r"computed in \d+s"), "computed in <T>"),
    (re.compile(r"^figures written to .*$", re.M), "figures written to <FIGDIR>"),
]


def normalise(text: str) -> str:
    for rx, rep in _TIME_TOKENS:
        text = rx.sub(rep, text)
    return text.rstrip() + "\n"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_mkfig() -> str:
    proc = subprocess.run([sys.executable, os.path.join("code", "mkfig_zip50.py")],
                          cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"mkfig_zip50.py exited {proc.returncode}\n{proc.stderr[-4000:]}")
    return normalise(proc.stdout)


def figure_hashes() -> dict:
    return {f: sha256(os.path.join(ROOT, "figures", f)) for f in FIGURES}


def write_anchors(stdout: str) -> None:
    os.makedirs(ANCHORS, exist_ok=True)
    with open(STDOUT_ANCHOR, "w") as fh:
        fh.write(stdout)
    with open(SHA_ANCHOR, "w") as fh:
        for f, h in figure_hashes().items():
            fh.write(f"{h}  figures/{f}\n")


def read_sha_anchor() -> dict:
    out = {}
    with open(SHA_ANCHOR) as fh:
        for line in fh:
            h, _, p = line.strip().partition("  ")
            out[os.path.basename(p)] = h
    return out


def test_zip50_anchor():
    assert os.path.exists(STDOUT_ANCHOR) and os.path.exists(SHA_ANCHOR), \
        "anchors missing -- run test_zip50_anchor.py --update once on a clean solver"
    want_sha = read_sha_anchor()
    with open(STDOUT_ANCHOR) as fh:
        want_out = fh.read()
    got_out = run_mkfig()
    if got_out != want_out:
        import difflib
        diff = "".join(difflib.unified_diff(want_out.splitlines(True), got_out.splitlines(True),
                                            "anchor", "now", n=2))
        raise AssertionError("mkfig_zip50.py stdout drifted from anchor:\n" + diff[:6000])
    got_sha = figure_hashes()
    bad = [f for f in FIGURES if got_sha[f] != want_sha.get(f)]
    assert not bad, f"figure hashes drifted: {bad}"


if __name__ == "__main__":
    if "--update" in sys.argv:
        out = run_mkfig()
        write_anchors(out)
        print("anchors written to", ANCHORS)
    else:
        test_zip50_anchor()
        print("zip50 anchor: OK")
