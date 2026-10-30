// audit: checks tools/snowflake's documents against its code, the owner's queries and the run outputs, with
// DATA_MODEL.md as the reference (DATASET_LOG.md, Conventions, Audit).  Read-only: it writes nothing.
// Run from the worktree root:
//   subagent({ workflow: "tools/snowflake/audit.js", cwd: "<worktree>", async: true, args: { since: "2026-10-30" } })
// args: { since: "YYYY-MM-DD" (log entries dated on or after it), td_repo: "/Users/Shared/sv-ntlee/td" (optional),
//         extra: ["path", ...] (optional files whose claims are checked too, e.g. a handoff note) }
// Step 1, reader: numbered claims, one per line.  Step 2, auditors in parallel batches of 60: one row per claim.
// Returns { claims, batches: [{ first, last, ok, output }] }; the session records the outcome as a log entry.
if (!/^\d{4}-\d{2}-\d{2}$/.test(args.since || "")) throw new Error("audit needs args.since as YYYY-MM-DD");
const td = args.td_repo || "/Users/Shared/sv-ntlee/td";
const extra = Array.isArray(args.extra) ? args.extra : [];

const sources = [
  "Evidence you may read (read-only):",
  "- the repo: tools/snowflake/ (SQL, the DuckDB test explore/profile_test.sh), notes/",
  "- the owner's queries: " + td + "/owner_sql/*.sql (git-excluded); a cite `s1_opp_sales.sql:N` is " + td + "/owner_sql/s1_opp_sales.sql line N,",
  "  at the version whose sha256 prefix the citing log entry pins (check with `shasum -a 256`)",
  "- run outputs the entries name: " + td + "/data/safe/*.csv (the owner's runs; counts and $ only)",
  "- the archived log: `git show archive/snowflake-2026-10:tools/snowflake/DATASET_LOG.md` (a cite 'archived log, line N')",
];

const fixedClaims = [
  "K1 | No carrier name (the table-name prefixes in " + td + "/owner_sql/vars.sql and the companies they stand for) appears under tools/snowflake/ or in notes/2026-10-*; SQL reads a carrier-named table only through IDENTIFIER($name) set by a SET line holding a <...> placeholder | DATASET_LOG.md, Conventions, Table variables and Masking | grep",
  "K2 | No person's name (wholesaler, RVP, DVP, advisor, colleague) appears under tools/snowflake/ or in notes/2026-10-* | DATASET_LOG.md, Conventions, Masking | grep",
  "K3 | No sales amount appears next to a firm name under tools/snowflake/ or in notes/2026-10-* | DATASET_LOG.md, Conventions, Masking | grep",
  "K4 | Each Run All file under tools/snowflake/ written after the One result convention ends on one statement that returns every part the owner reads (explore/schema.sql predates it) | DATASET_LOG.md, Conventions, One result | the SQL files",
  "K5 | Every cite into owner_sql/<file>:N quotes or describes that line of the file version the citing entry pins | DATASET_LOG.md, Conventions, Owner's queries | owner_sql + shasum",
  "K6 | Every Q number DATA_MODEL.md names is in DATASET_LOG.md's open index or its Settled section; every index row's 'since' date has a log entry or archived-log entry behind it | DATA_MODEL.md, DATASET_LOG.md | both files",
];

const extract = await runs.run("claims", {
  agent: "reader",
  task: [
    "Question: which checkable claims do tools/snowflake's documents make? List them; do not judge them.",
    "Read fully: tools/snowflake/DATA_MODEL.md, tools/snowflake/README.md, and tools/snowflake/DATASET_LOG.md",
    "(Conventions, Settled, Parked, Open questions, and every Log entry dated " + args.since + " or later)" +
      (extra.length ? "; also " + extra.join(", ") : "") + ".",
    "A claim is one checkable statement: a fact about the data, a number, a file:line cite and what it says, a status",
    "('settled', 'given', 'open: Q..'), an owner decision with its date, or what a SQL file or test does. Every row of",
    "DATA_MODEL.md's tables that states a fact or a status is at least one claim. Skip opinions and plans.",
    "Output only lines of the form, numbered from C1, one claim per line, nothing else:",
    "C<n> | <the claim, one sentence, masked as the document masks it> | <where stated: file:line> | <the evidence it names: file:line, a CSV, 'archived log, line N', or none>",
  ].join("\n"),
});
if (!extract.ok) throw new Error("claim extraction failed: run " + extract.runId);
const claims = extract.output.split("\n").map((l) => l.trim()).filter((l) => /^C\d+ \|/.test(l)).concat(fixedClaims);
if (claims.length === fixedClaims.length) throw new Error("the reader returned no C<n> lines; run " + extract.runId);

const size = 60;
const batches = [];
for (let i = 0; i < claims.length; i += size) batches.push(claims.slice(i, i + size));
const results = await runs.all(batches.map((b, i) => ({
  key: "audit-" + i,
  label: "Audit claims " + (i * size + 1) + "-" + (i * size + b.length),
  agent: "auditor",
  task: [
    "Audit these claims of tools/snowflake (repo root = cwd). DATA_MODEL.md is the model; where a SQL file or query and",
    "a document disagree, the code decides (DATA_MODEL.md says so). A number is Verified only if the cited CSV or file",
    "yields it; a cite only if the line says what the claim says. Never print a person's name; firm names may be quoted.",
    ...sources,
    "Claims (id | claim | where stated | evidence named):",
    ...b,
  ].join("\n"),
})));
return {
  claims: claims.length,
  batches: results.map((r, i) => ({ first: i * size + 1, last: i * size + batches[i].length, ok: r.ok, runId: r.runId, output: r.output })),
};
