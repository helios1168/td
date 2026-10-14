"""Presentation copy of a run's ZIP map: plain title, no footer. Not the tracked render."""
import os, sys, importlib.util
import matplotlib.figure as mf
HERE = os.path.join(os.getcwd(), "tools", "maps")
spec = importlib.util.spec_from_file_location("zip_pages", os.path.join(HERE, "zip_pages.py"))
zp = importlib.util.module_from_spec(spec); spec.loader.exec_module(zp)
run_dir, title, out_dir = sys.argv[1:4]
_text = mf.Figure.text
mf.Figure.text = lambda self, x, y, *a, **k: None if y < 0.1 else _text(self, x, y, *a, **k)  # drop the footer lines
mf.Figure.suptitle = (lambda orig: lambda self, s, **k: orig(self, title, **k))(mf.Figure.suptitle)
print(zp.main([run_dir, title, out_dir, "--corridor"]))
