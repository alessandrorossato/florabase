# SQLite in the backend image: triage and reference-index hardening (7 November 2026)

## Findings

Grype v0.121.1 (advisory second scanner) reports four High findings in the backend's
`sqlite-libs 3.53.4-r0` (Alpine 3.24). The release gate's pinned Trivy 0.69.3 reports none of them,
and Alpine has no fixed package yet. All four are NVD "Analyzed", matched by the CPE
`cpe:2.3:a:sqlite:sqlite:3.53.4`. None is on SQLite's list of rejected reports. The three library
bugs have real upstream fixes, released in 3.54.0.

| CVE | Component | Disposition | Basis |
| --- | --- | --- | --- |
| CVE-2026-119373 | FTS5 `fts5MergeRowidLists()` (detail=none prefix doclists with negative rowids) | Not exploitable under verified runtime conditions | Florabase creates no FTS5 table and issues no `MATCH`. The only path was a crafted reference index (below), now refused before any query |
| CVE-2026-119374 | FTS5 secure-delete on a corrupted index | Not exploitable | Needs a delete. Every reference connection is read-only and `query_only`, and FTS5 objects are refused |
| CVE-2026-119379 | Session extension `sqlite3changeset_apply()` | Not exploitable | Python's `sqlite3` exposes no session API, `_sqlite3` references no session symbols, and extension loading is disabled on every connection |
| CVE-2026-119586 | `sqlite3` command-line shell `.recover` | Not affected | The CLI is not installed and `libsqlite3` has no recover API; the CPE match is to the shared product name |

Independent QA of `4329381` agreed with all four, and demonstrated the 119373 residual. A file
whose `taxa` is a view over a detail=none FTS5 table made Florabase's unchanged WCVP search run an
FTS5 prefix `MATCH` over negative rowids. `trusted_schema=OFF` blocks the view route but not a
`taxa` that is itself an FTS5 table, so a schema allow-list is the decisive control. The operator
approved hardening before public publication.

## Hardening

`backend/src/florabase/core/reference_index.py::open_reference_index` is now the only way the WFO
(`taxonomy/source.py`) and WCVP (`native_range_enrichment/source.py`) readers open an index. On
every connection, before any application statement:

1. Open the file with `mode=ro`.
2. `setconfig`: `DEFENSIVE` on; `TRUSTED_SCHEMA`, `ENABLE_VIEW`, `ENABLE_TRIGGER`,
   `ENABLE_LOAD_EXTENSION` and `WRITABLE_SCHEMA` off. Each value is read back with `getconfig`,
   and the open fails if one did not apply.
3. `PRAGMA query_only=ON`, `PRAGMA cell_size_check=ON`, and an attached-database limit of 0
   (`ATTACH` is refused).
4. `BEGIN`: one read transaction, and its shared lock, from the check until the connection
   closes, so a cooperating writer cannot change the schema between the check and the queries.
5. Read `sqlite_schema` (type, name, table, SQL) and require it to equal the builder's contract
   exactly, with no duplicated row (a second automatic index pointing at other storage would
   otherwise collapse into the same set). Reading the schema does not instantiate virtual
   tables; a test with a non-existent module proves it.

A mismatch raises a generic, actionable error, for example "The WCVP snapshot is not a supported
index built by Florabase's WCVP builder." It reaches the API as a 503 `*_unavailable` response
that contains no object name or SQL. The backend log gets a warning naming the unexpected and
missing objects (quoted and bounded). Nothing is written: the tests compare the directory's bytes
and modification times before and after a refusal.

Both builders run the same check on their temporary output and refuse to publish an index the
reader would refuse.

### Supported index compatibility

Each builder has written exactly one layout since it was introduced (WFO: TAXONOMY-003, metadata
`format_version` 1; WCVP: ENRICHMENT-001, the same layout for reviewed releases 15 and 16). The
builder DDL is unchanged, and the contracts are exactly what the builders at `4329381` wrote, so
every index built by a supported Florabase builder remains accepted. Rejected now: any index not
in that layout, including indexes with an `ANALYZE` (`sqlite_stat1`) table, extra or dropped
indexes, added columns, renamed tables, views, triggers and virtual tables. The previous checks
are unchanged: metadata, release, the WFO format version and the WFO seal.

### Evaluated and not adopted

- `PRAGMA quick_check` at open would scan the whole file (400 MB to 1 GB) on request paths. It
  does not inspect FTS5 structures, the relevant attack surface, and once virtual tables are
  refused, `cell_size_check` covers B-tree cell corruption on the pages actually read.
- `immutable=1` would disable SQLite's change detection and locking; the shared read transaction
  is the safer way to keep the checked schema in force.

## Evidence

- `backend/tests/test_reference_index.py` (25 cases) covers:
  - builder output equals the contracts (WFO; WCVP 15 and 16), and reference operations on them;
  - the hardened connection state, with writes and `load_extension` refused;
  - QA's view-over-FTS5 exploit: the control connection runs the MATCH, while every WCVP
    operation is refused with no write;
  - hardening alone stops the view but not a direct FTS5 `taxa`, so the contract decides;
  - views, triggers, FTS5, an unknown module, an extra table, an extra or dropped index,
    `sqlite_stat1`, an added column and a renamed `taxa`, each with a matching seal;
  - a duplicated schema row and a refused `ATTACH`;
  - empty, non-SQLite, damaged-header and truncated files;
  - an unsupported WFO format version and a WCVP release mismatch;
  - builders refusing to publish a non-conforming layout.
- These tests and the existing WFO/WCVP suites (91 cases) passed on SQLite 3.40.1 (development
  image) and on SQLite 3.53.4 inside the backend `runtime` image built from this tree.
- Performance, runtime image, a builder-made WCVP index of 1,400,000 taxa and 700,000
  distributions (408 MB):
  - connection open went from a median of 0.044 ms to 0.117 ms;
  - search, which opens two connections, went from 0.50 to 0.59 ms (25 rows), 0.37 to 0.46 ms
    (12 rows) and 0.25 to 0.32 ms (no rows);
  - results were identical;
  - the builder's self-check costs 0.24 ms.
- Not done: building indexes from the full official WFO/WCVP archives (none on this host;
  downloading them was not part of this change). The layout depends only on the builder DDL,
  which is unchanged.

## Remaining risk

- SQLite 3.53.4 stays until Alpine ships 3.54.x or a patched 3.53.4-rN. Rebuild the backend then;
  this is ordinary base maintenance.
- A file with the exact expected schema but crafted B-tree contents still reaches SQLite's core
  parser. That is SQLite's documented corrupt-database threat model, mitigated by defensive mode
  and `cell_size_check`. Building the index yourself (provenance) remains the primary control; see
  the [installation guide](../../installation.md#optional-botanical-reference-datasets).
- A writer that ignores SQLite locking and rewrites the file in place while it is open would need
  write access to the root-owned, read-only-mounted `reference/` directory, which is host-root
  level.
