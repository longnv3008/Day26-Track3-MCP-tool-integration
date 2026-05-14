# Design: Database MCP Server with FastMCP and SQLite

**Date:** 2026-05-14  
**Lab:** Day26-Track3-MCP-tool-integration  
**Status:** Approved

---

## Goal

Build a FastMCP server backed by SQLite that exposes `search`, `insert`, and `aggregate` tools plus two schema resources. The server must connect to both Claude Code and MCP Inspector, with optional HTTP/SSE transport as bonus.

---

## Architecture

### Approach

Layered separation following the pseudocode structure: DB adapter layer isolated from MCP tool layer. Each file has one clear responsibility.

### File Structure

```
implementation/
  db.py              — SQLiteAdapter class (all SQL logic + validation)
  init_db.py         — Schema DDL + seed data, creates lab.db
  mcp_server.py      — FastMCP server: 3 tools, 2 resources, argparse transport
  verify_server.py   — Repeatable smoke test script
  tests/
    test_server.py   — Unit tests for SQLiteAdapter and tool handlers
  lab.db             — SQLite file (generated, not committed)
  start_inspector.sh — Launches MCP Inspector with correct paths
  .mcp.json          — Claude Code client config
```

---

## Data Model

```sql
students(id INTEGER PK, name TEXT, cohort TEXT, score REAL)
courses(id INTEGER PK, title TEXT, credits INTEGER)
enrollments(id INTEGER PK, student_id INTEGER FK, course_id INTEGER FK, grade TEXT)
```

Seed data: ~5 students across cohorts A1/A2, ~3 courses, ~6 enrollments.

---

## Components

### `db.py` — SQLiteAdapter

Responsibilities:
- `connect()` — returns sqlite3 connection with `row_factory = sqlite3.Row`
- `list_tables()` — queries `sqlite_master`, returns non-internal table names
- `get_table_schema(table)` — runs `PRAGMA table_info(table)`, returns list of `{name, type, pk, notnull}`
- `_validate_identifier(name, allowed)` — checks name against known table/column whitelist, raises `ValidationError` if unknown
- `search(table, columns, filters, limit, offset, order_by, descending)` — builds parameterized SELECT
- `insert(table, values)` — builds parameterized INSERT, returns inserted row with id
- `aggregate(table, metric, column, filters, group_by)` — builds `SELECT metric(col)` query

`ValidationError(Exception)` raised for any invalid input; caught at tool handler level.

### `init_db.py`

- Defines `SCHEMA_SQL` (CREATE TABLE statements)
- Defines `SEED_SQL` (INSERT statements)
- `create_database(path)` — opens/creates `lab.db`, executes schema + seed, commits, returns path
- Idempotent: uses `CREATE TABLE IF NOT EXISTS`

### `mcp_server.py`

```python
mcp = FastMCP("SQLite Lab MCP Server")
adapter = SQLiteAdapter("lab.db")
```

**Tool `search`**
- Params: `table: str`, `columns: list[str] | None`, `filters: dict | None`, `limit: int = 20`, `offset: int = 0`, `order_by: str | None`, `descending: bool = False`
- Returns: `{"rows": [...], "count": N, "table": "..."}`

**Tool `insert`**
- Params: `table: str`, `values: dict`
- Returns: `{"inserted": {...}, "id": N}`

**Tool `aggregate`**
- Params: `table: str`, `metric: str`, `column: str | None`, `filters: dict | None`, `group_by: str | None`
- Allowed metrics: `count`, `avg`, `sum`, `min`, `max`
- Returns: `[{"group": val, "value": N}, ...]` or `[{"value": N}]`

**Resource `schema://database`**
- Returns JSON: `{"tables": {"students": [...columns], "courses": [...], "enrollments": [...]}}`

**Resource `schema://table/{table_name}`**
- Validates `table_name` against known tables
- Returns JSON: `{"table": "students", "columns": [{name, type, pk, notnull}, ...]}`

**Transport (argparse):**
- Default: `mcp.run()` → stdio
- `--transport http --port 8000` → `mcp.run(transport="http", port=8000)` (bonus)

### `verify_server.py`

Connects to server via MCP Python client over stdio, runs checks in sequence:
1. List tools → assert `search`, `insert`, `aggregate` present
2. List resources → assert `schema://database` present
3. `search("students")` → assert rows returned
4. `insert("students", {"name": "Test", "cohort": "A1", "score": 95.0})` → assert id returned
5. `aggregate("students", "avg", "score")` → assert numeric result
6. `search("nonexistent_table")` → assert error message returned

### `tests/test_server.py`

Unit tests using `pytest` + `tmp_path` fixture:
- `test_search_valid` — returns rows from students
- `test_search_invalid_table` — raises `ValidationError`
- `test_search_invalid_column` — raises `ValidationError`
- `test_search_invalid_operator` — raises `ValidationError`
- `test_insert_valid` — inserts and returns id
- `test_insert_empty_values` — raises `ValidationError`
- `test_aggregate_count` — returns integer
- `test_aggregate_invalid_metric` — raises `ValidationError`
- `test_schema_resource` — returns all tables

---

## Validation Rules

| Check | Rule |
|-------|------|
| Table name | Must be in `list_tables()` result |
| Column name | Must be in `get_table_schema(table)` result |
| Filter operator | Must be in `{eq, ne, gt, lt, gte, lte, like}` |
| Metric | Must be in `{count, avg, sum, min, max}` |
| Insert values | Must not be empty dict |
| SQL parameters | Always use `?` placeholders, never string concat |

---

## Client Configuration

### Claude Code (`.mcp.json`)
```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "python",
      "args": ["ABSOLUTE_PATH/implementation/mcp_server.py"],
      "env": {}
    }
  }
}
```

### MCP Inspector (`start_inspector.sh`)
```bash
#!/bin/bash
mkdir -p .npm-cache
NPM_CONFIG_CACHE="$PWD/.npm-cache" npx -y @modelcontextprotocol/inspector \
  python implementation/mcp_server.py
```

---

## Bonus

- HTTP/SSE transport via `--transport http --port 8000` (5 pts)
- PostgreSQL adapter behind shared interface (3 pts) — **out of scope for this implementation**
- Pagination guidance in search docstring (2 pts)

---

## Scoring Targets

| Category | Points | How Met |
|----------|--------|---------|
| Server Foundation | 20 | clean structure, reproducible init_db, separated layers |
| Required Tools | 30 | search/insert/aggregate all implemented |
| MCP Resources | 15 | schema://database + schema://table/{name} |
| Safety & Errors | 15 | whitelist validation, parameterized SQL |
| Verification | 10 | verify_server.py + pytest |
| Client Integration | 10 | .mcp.json + start_inspector.sh + README |
| Bonus | +5 | HTTP/SSE transport |
| **Total** | **105** | |
