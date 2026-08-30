# math_note -- standalone LaTeX note with computed toy figures.
# `make` regenerates the toy figures + numbers, then builds math_note.pdf.
# MacTeX lives at /Library/TeX/texbin, which is NOT on PATH in non-interactive
# shells (CLAUDE.md); exported here so `make` works from scripts and agents.

PY      := ../../../.venv/bin/python3
export PATH := /Library/TeX/texbin:$(PATH)

all: math_note.pdf

toy_path_numbers.tex figures/toy_path.png: toy_path.py
	$(PY) toy_path.py

toy_grid_numbers.tex figures/toy_grid.png: toy_grid.py
	$(PY) toy_grid.py

toy_numbers.tex: toy_path_numbers.tex toy_grid_numbers.tex
	cat toy_path_numbers.tex toy_grid_numbers.tex > $@

math_note.pdf: math_note.tex toy_numbers.tex figures/toy_path.png figures/toy_grid.png \
               ../../../literature/territory_bibliography.bib
	latexmk -pdf math_note.tex

clean:
	latexmk -C math_note.tex 2>/dev/null || true
	rm -f math_note.bbl toy_numbers.tex toy_path_numbers.tex toy_grid_numbers.tex

.PHONY: all clean
