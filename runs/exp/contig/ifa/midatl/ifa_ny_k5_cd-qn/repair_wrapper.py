import importlib.util
import json
import os
import sys

path = '/Users/sandvault-ntlee/.pi/worktrees/ifa-ny/tools/exp/contig/repair.py'
spec = importlib.util.spec_from_file_location('ny_qn_repair', path)
repair = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = repair
spec.loader.exec_module(repair)
original = repair._repair_neck

def queens_only(inst, plan, owner, j, side, *args, **kwargs):
    if '10001' in side:
        print(f'SKIP exhausted Manhattan neck: {j} 10001 ({len(side)} ZIPs)', flush=True)
        return owner
    return original(inst, plan, owner, j, side, *args, **kwargs)

repair._repair_neck = queens_only
code = repair.main()
out = sys.argv[sys.argv.index('--out') + 1]
manifest = os.path.join(out, 'manifest.json')
with open(manifest) as fh:
    doc = json.load(fh)
doc['notes'] = {'wrapper': os.path.abspath(__file__), 'repair_source': path,
                'skip': 'Exhausted Manhattan neck whose cut-off side contains ZIP 10001; unchanged exemption semantics.',
                'gate': 'Default; TD_NECK_GAP_WIDTH unset.', 'argv': sys.argv[1:]}
with open(manifest, 'w') as fh:
    json.dump(doc, fh, indent=2, sort_keys=True)
    fh.write('\n')
sys.exit(code)
