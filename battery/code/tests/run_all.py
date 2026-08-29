"""
run_all.py -- plain test runner for battery/code/tests (pytest-compatible layout).

Discovers every `test_*.py` in this directory, imports it, and runs every callable
whose name starts with `test_`.  A module that sets `SLOW = True` is skipped unless
the environment variable `TD_SLOW=1` is set (the zip50 anchor takes ~2 min).

Run from the repo root:
    .venv/bin/python3 battery/code/tests/run_all.py            # fast tests
    TD_SLOW=1 .venv/bin/python3 battery/code/tests/run_all.py  # + anchors
    .venv/bin/python3 battery/code/tests/run_all.py -k base    # name filter

Exit status is nonzero if any test fails.  Also works under `pytest battery/code/tests`.
"""
from __future__ import annotations
import importlib.util, os, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)


def _load(path):
    name = "tests." + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    pattern = None
    if "-k" in argv:
        pattern = argv[argv.index("-k") + 1]
    slow = os.environ.get("TD_SLOW", "0") not in ("", "0")
    os.chdir(ROOT)                      # every script assumes the repo root
    files = sorted(f for f in os.listdir(HERE) if f.startswith("test_") and f.endswith(".py"))
    n_pass = n_fail = n_skip = 0
    failures = []
    for f in files:
        mod = _load(os.path.join(HERE, f))
        if getattr(mod, "SLOW", False) and not slow:
            print(f"SKIP  {f}  (set TD_SLOW=1)")
            n_skip += 1
            continue
        tests = [(k, v) for k, v in vars(mod).items()
                 if k.startswith("test_") and callable(v)]
        for name, fn in tests:
            full = f"{f}::{name}"
            if pattern and pattern not in full:
                n_skip += 1
                continue
            t0 = time.time()
            try:
                fn()
                n_pass += 1
                print(f"PASS  {full}  ({time.time()-t0:.1f}s)")
            except Exception:
                n_fail += 1
                failures.append(full)
                print(f"FAIL  {full}  ({time.time()-t0:.1f}s)")
                traceback.print_exc()
    print(f"\n{n_pass} passed, {n_fail} failed, {n_skip} skipped")
    if failures:
        print("failures:", *failures, sep="\n  ")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
