---
type: Lesson
title: 'A zip_pages.pdf page''s title is part of the page image, so pdftotext cannot verify page order: render pages with pdftoppm and read them (pdfunite appends rendered map PDFs unchanged)'
description: 'Consolidating the seven IFA zip_pages.pdf files into one stakeholder PDF: pdfunite appends the files unchanged (14 pages, ~4.6 MB, branch m5-studio/ifa-pages-all, d33af85), but pdftotext -layout extracts no page-identifying text because the titles are part of the page image — order was verified by rendering the first and last pages to 40 dpi PNGs with pdftoppm and reading them (page 1 = K48 summary, page 14 = K54 district page). Rendered map PDFs are verified visually; an embedded text title would make the check automatable.'
tags:
- lesson
- rendering
- pdf
- pdfunite
- verification
- zip-pages
- stakeholders
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-21T08:18:32Z
state: STAGED
kind: lesson
evidence:
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#32c98bbb
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#a22f1967
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#e5767de0
uses: []
supersedes: null
history:
- {at: '2026-10-21T08:18:32Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

The owner asked (2026-10-18) to consolidate the seven IFA map packages (`results/ifa_pages_2026-10-17/K48..K54/zip_pages.pdf`, on `main`) into one PDF by appending the originals unchanged.

What worked:
- `pdfunite` was already installed and joins the ordered list of PDFs in one command. The seven files were appended unchanged, K48 first and K54 last: 14 pages (a summary page and a district page per map), about 4.6 MB (branch `m5-studio/ifa-pages-all`, d33af85; the seven per-K PDFs remain where they were).
- The verification trap: `pdftotext -layout` extracts nothing that identifies a page — the titles ("IFA 48 districts" etc.) are drawn into the page image, not a text layer, so an order check from extracted text was impossible for `zip_pages.pdf` output.
- The check that worked: render pages with `pdftoppm -r 40 -f <n> -l <n>` to small PNGs and read them — the first page (K48 summary) and the last (K54 district page) confirmed the K order across the file.

Durable rule: a page-append of rendered map PDFs is verified from rendered pages (or anything that survives rasterization), never from text extraction — and if the renderer ever grows an embedded text title, the order check becomes automatable and should be added wherever map packages are assembled.
