.PHONY: all clean

TEX := nash_territory_division_20260826.tex
PDF := $(TEX:.tex=.pdf)

all: $(PDF)

$(PDF): $(TEX)
	latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX)

clean:
	latexmk -c $(TEX)
	rm -f $(PDF:.pdf=.bbl)
