"""Every district still in pieces in a run's realise.json, with the repair's reasons.

    unrepaired.py RUN_DIR [RUN_DIR ...]
"""
import json
import os
import sys


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("unrepaired", "stuck") and v:
                yield path + "/" + k, v
            else:
                yield from walk(v, path + "/" + k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")


for d in sys.argv[1:]:
    r = json.load(open(os.path.join(d, "realise.json")))
    print("===", os.path.basename(d.rstrip("/")))
    for where, v in walk(r):
        items = v.items() if isinstance(v, dict) else enumerate(v)
        for key, val in items:
            print(f"  {where}  {key}: {json.dumps(val)[:300]}")
