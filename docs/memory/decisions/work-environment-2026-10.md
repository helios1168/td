# Running td in the owner's work environment

**Status:** recommendations made 2026-10-02 in td session 01a0fd88, not changes to td. The owner asked to run their own scenarios inside their work Snowflake environment, then said ML Jobs were likely unavailable, then chose a local Windows machine (Intel Core vPro i7). Facts: `facts/portability`.

**Decision.**
- **Snowflake, first answer:** ML Jobs (`snowflake.ml.jobs.submit_directory`) over a stored procedure or a headless notebook.
- **Snowflake without ML Jobs:** a stored procedure that installs from the PyPI mirror (`ARTIFACT_REPOSITORY = snowflake.snowpark.pypi_shared_repository`), over the Anaconda channel.
- **Windows:** set `PYTHONUTF8=1` on the work machine instead of changing code in the bundle.

**Alternatives rejected.**
- A stored procedure or headless notebook ahead of ML Jobs: whether highspy and pyproj install in a stored procedure was unverified, and notebook arguments are split on whitespace.
- The Anaconda channel: it needs a code change for GEOS 3.10 and gives different plans because of highspy 1.13.1.
- Fixing the text encoding in the bundle: a code fix has to go through an issue, and the bundle should stay byte-identical to commit 9583135.

**Consequences.** The two `encoding=` fixes (`td/spec.py:229`, `td/geo.py:598`) remain open work for an issue. A Windows or Snowflake port can be checked against the cross-platform reference run in `facts/portability`.
