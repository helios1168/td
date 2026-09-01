# channel_note -- standalone LaTeX note on the national-channel districting problem.
# `make` regenerates the computed numbers + the ceiling figure, then builds
# channel_note.pdf.  MacTeX lives at /Library/TeX/texbin, which is NOT on PATH in
# non-interactive shells (CLAUDE.md); exported here so `make` works from scripts
# and agents.

# The repo venv, whether this tree is the repo itself or a worktree under
# <repo>/.claude/worktrees/<unit>/ (which has no venv of its own).
PY      := $(firstword $(wildcard ../../.venv/bin/python3 \
                                  ../../../../../.venv/bin/python3) python3)
export PATH := /Library/TeX/texbin:$(PATH)

all: channel_note.pdf

ceiling_numbers.tex figures/draw_k13.png: ceiling.py
	$(PY) ceiling.py

channel_note.pdf: channel_note.tex ceiling_numbers.tex figures/draw_k13.png \
                  references.bib
	latexmk -pdf channel_note.tex

clean:
	latexmk -C channel_note.tex 2>/dev/null || true
	rm -f channel_note.bbl ceiling_numbers.tex

.PHONY: all clean
