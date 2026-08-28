# Literature review here, reuse anywhere

A workflow for building a verified bibliography in a compute-enabled session, then handing it to
ordinary Claude chats and Projects so future conversations cite accurately without re-searching.

The output is a file, not a conversation. That is the whole point: a chat is gone next week, an
annotated bibliography attached to a Project is knowledge every future chat in that Project reads.

---

## Why bother

Two failure modes make unverified citation expensive.

**Fabrication.** A plausible author-year-journal triple is easy to generate and hard to spot. The
fix is mechanical: resolve the DOI. A citation either resolves to a real paper saying what you
claim, or it does not.

**Silent incompleteness.** Keyword search returns what shares vocabulary with your query, not what
the field considers foundational. The seminal paper often uses different words — it named the
field before the current terms existed. Citation-graph traversal finds it; keyword search does not.

A verified bibliography fixes both once, then amortises across every future chat that reads it.

---

## The workflow

### 1. Fan out broad, expect noise

Run 6-10 conceptual queries covering the problem's distinct literatures. Batch them in one call.

Expect low precision. Scholarly search ranks over title, abstract *and* full text, so broad
multi-word queries surface heavily-cited papers from unrelated fields that share vocabulary. In
the run this workflow came from, "sales territory alignment salesforce districting optimization"
returned a paper on GPT-3 news summarisation as its top hit. Two of eight queries landed. That is
a normal yield and not a reason to stop.

The purpose of this pass is not the papers. It is to learn which of your guesses about the
relevant literatures are real.

### 2. Switch to near-title queries

Once you suspect a specific paper exists, query something close to its title. "Experiences with a
sales districting model criteria implementation" returns Hess & Samuels 1971 as the top hit;
"COSTA contribution optimizing sales territory alignment" returns Skiera & Albers 1998.

This is the highest-yield step, and it depends on prior knowledge: your recall proposes the
target, retrieval confirms it exists and supplies the correct metadata. Recall alone gives you a
citation you cannot defend; retrieval alone will not surface a 1971 paper.

### 3. Resolve every DOI, including the ones you are sure of

Fetch each work by DOI and check the returned title, authors, and year against what you expected.
Resolving a DOI you already know costs a second and converts a claim about a citation into a
citation.

This step catches real errors. In the source run, OpenAlex returned the author of Nash's 1953
*Two-Person Cooperative Games* as "John C. Nash" rather than John F. Nash. Metadata is not
authoritative merely because it came from a database — but you can only notice a discrepancy if
you look at the record.

Check the retraction flag in the same pass.

### 4. Walk the citation graph one step

Take the two or three most central hits and pull both directions: their reference lists
(backward) and their citing works (forward).

Backward finds the foundations. Forward finds the recent work that extends or contests them.
Neither reliably appears in keyword search. In the source run, a forward walk on a 2005
retrospective surfaced the entire modern commercial-districting thread — two papers that became
central to the review and that no keyword query had returned.

### 5. Annotate for reuse, not for storage

This is what makes the artifact useful later, and it is the step usually skipped. For each entry
write two things:

- **What it establishes** — the paper's actual contribution, one or two sentences.
- **Why it bears on your problem** — what you would cite it *for*, and against which claim.

A bibliography with only metadata tells a future reader that papers exist. A bibliography with
relevance notes tells them which one to reach for. The second is worth attaching to a Project;
the first is a list.

Note the gaps explicitly too — the threads you know are relevant and did not search. Without
that, absence reads as coverage.

### 6. Emit three formats

- **Annotated markdown** — the Project knowledge file. This is the deliverable.
- **CSV** — sortable, filterable, diffable when you extend it.
- **BibTeX** — drops into a manuscript with no retyping.

Same data, three consumers. Generate them from one structured source so they cannot drift.

---

## Handing it to standard Claude

**Projects.** Attach the markdown as Project knowledge. Every chat in that Project reads it, so
"what's the citation for the EF1 result" is answered from the file rather than from recall. This
is the durable option and the one worth setting up.

**A single chat.** Paste the markdown at the head of the conversation. Same effect, one session.

**A framing line worth including**, whichever route you take:

> Cite only from the attached bibliography. If a claim needs a source that is not in it, say so
> rather than supplying one.

That converts the file from context into a constraint, which is what stops fabrication in the
chats that follow.

**Keeping it current.** Re-run steps 1-4 when the scope moves, and diff the CSV. New entries need
annotation; that is the only manual step in an otherwise reproducible pipeline.

---

## What needs a compute-enabled session and what does not

The scholarly APIs are public, and MCP connectors work in Claude Desktop too — so the *method*
is portable, and steps 1-5 can be done in any client that reaches a literature server.

What a compute session changes is throughput and reproducibility: 15-20 queries inside one call
rather than one query per exchange, results written to disk and filtered without re-reading them,
DOI verification as a loop over the whole set, and the three output formats generated from one
structured source by a script you can re-run.

In a chat client the same workflow costs one exchange per query, so in practice you run twelve
queries instead of forty-eight, and step 4 — the citation walk, the step that finds what keyword
search misses — is the one that gets dropped. The limit is attrition, not capability.

Reasonable division of labour: build and refresh the bibliography where the loop is cheap; write
the prose that cites it wherever you prefer to write.
