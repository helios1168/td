.PHONY: all clean

TEX := nash_territory_division.tex
BIB := literature/territory_bibliography.bib
PDF := $(TEX:.tex=.pdf)

all: $(PDF)

$(PDF): $(TEX) $(BIB) $(wildcard figures/*.png)
	latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX)

clean:
	latexmk -c $(TEX)
	rm -f $(PDF:.pdf=.bbl)
