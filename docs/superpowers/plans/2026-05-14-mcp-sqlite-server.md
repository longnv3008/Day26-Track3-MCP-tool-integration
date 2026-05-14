# MCP SQLite Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastMCP server backed by SQLite that exposes `search`, `insert`, `aggregate` tools plus two schema resources, connectable from Claude Code and MCP Inspector.

**Architecture:** Layered: `db.py` (SQLiteAdapter + ValidationError) is the pure DB layer; `mcp_server.py` wraps it with FastMCP decorators; `init_db.py` creates and seeds `lab.db`; `verify_server.py` runs a headless smoke test via the MCP Python client.

**Tech Stack:** Python 3.12, FastMCP 3.2.4, mcp 1.27.1, SQLite3 (stdlib), pytest 9.0.3

**Python Executable:** `C:\Users\LONG NGO\AppData\Local\Programs\Python\Python312\python.exe`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `implementation/db.py` | Create | SQLiteAdapter: validation, search, insert, aggregate |
| `implementation/init_db.py` | Create | Schema DDL + seed data + create_database() |
| `implementation/mcp_server.py` | Create | FastMCP server: 3 tools, 2 resources, argparse transport |
| `implementation/verify_server.py` | Create | Headless MCP client smoke test |
| `implementation/tests/__init__.py` | Create | Empty, marks tests as package |
| `implementation/tests/test_server.py` | Create | Unit tests for SQLiteAdapter |
| `implementation/start_inspector.sh` | Create | Launches MCP Inspector |
| `implementation/start_inspector.bat` | Create | Windows equivalent for Inspector |
| `implementation/.mcp.json` | Create | Claude Code client config |
| `implementation/requirements.txt` | Create | Pinned deps |
| `implementation/.gitignore` | Create | Ignores lab.db and __pycache__ |

---

## Task 1: Project Setup

**Files:**
- Create: `implementation/requirements.txt`
- Create: `implementation/.gitignore`
- Create: `implementation/tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
mkdir -p implementation/tests
```

- [ ] **Step 2: Create requirements.txt**

```
# implementation/requirements.txt
fastmcp>=3.2.4
mcp>=1.24.0
pytest>=9.0.0
```

- [ ] **Step 3: Create .gitignore**

```
# implementation/.gitignore
lab.db
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
.npm-cache/
```

- [ ] **Step 4: Create tests/__init__.py**

Empty file — no content needed.

- [ ] **Step 5: Verify Python environment**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation"
python -c "import fastmcp, mcp, sqlite3; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git add implementation/
git commit -m "chore: scaffold implementation directory and requirements"
```

---

## Task 2: Database Schema and Seed Data (`init_db.py`)

**Files:**
- Create: `implementation/init_db.py`

- [ ] **Step 1: Create init_db.py**

```python
# implementation/init_db.py
import sqlite3
import os

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL,
    cohort  TEXT    NOT NULL,
    score   REAL    NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT    NOT NULL,
    credits INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS enrollments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id  INTEGER NOT NULL REFERENCES courses(id),
    grade      TEXT
);
"""

SEED_SQL = """
INSERT OR IGNORE INTO students (id, name, cohort, score) VALUES
    (1, 'Alice',  'A1', 92.5),
    (2, 'Bob',    'A1', 78.0),
    (3, 'Carol',  'A2', 88.5),
    (4, 'David',  'A2', 65.0),
    (5, 'Eve',    'A1', 95.0);
INSERT OR IGNORE INTO courses (id, title, credits) VALUES
    (1, 'Python Basics',    3),
    (2, 'Data Structures',  4),
    (3, 'Machine Learning', 4);
INSERT OR IGNORE INTO enrollments (id, student_id, course_id, grade) VALUES
    (1, 1, 1, 'A'),
    (2, 1, 2, 'B+'),
    (3, 2, 1, 'B'),
    (4, 3, 3, 'A-'),
    (5, 4, 2, 'C+'),
    (6, 5, 3, 'A');
"""


def create_database(path: str = "lab.db") -> str:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SEED_SQL)
    conn.commit()
    conn.close()
    return path


if __name__ == "__main__":
    db_path = create_database(
        os.path.join(os.path.dirname(__file__), "lab.db")
    )
    print(f"Database created: {db_path}")
```

- [ ] **Step 2: Run init_db.py to verify it works**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation"
python init_db.py
```

Expected output: `Database created: .../lab.db`

- [ ] **Step 3: Verify database contents**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('lab.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT * FROM students').fetchall()
for r in rows: print(dict(r))
conn.close()
"
```

Expected: 5 student rows printed.

- [ ] **Step 4: Commit**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git add implementation/init_db.py
git commit -m "feat: add init_db with students/courses/enrollments schema and seed"
```

---

## Task 3: Write Failing Tests for SQLiteAdapter (`tests/test_server.py`)

**Files:**
- Create: `implementation/tests/test_server.py`

- [ ] **Step 1: Create the test file**

```python
# implementation/tests/test_server.py
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import SQLiteAdapter, ValidationError
from init_db import create_database


@pytest.fixture
def adapter(tmp_path):
    db_path = str(tmp_path / "test.db")
    create_database(db_path)
    return SQLiteAdapter(db_path)


def test_list_tables(adapter):
    tables = adapter.list_tables()
    assert set(tables) == {"students", "courses", "enrollments"}


def test_get_table_schema(adapter):
    schema = adapter.get_table_schema("students")
    col_names = {c["name"] for c in schema}
    assert col_names == {"id", "name", "cohort", "score"}


def test_search_valid(adapter):
    result = adapter.search("students")
    assert "rows" in result
    assert len(result["rows"]) == 5
    assert result["table"] == "students"


def test_search_with_filter(adapter):
    result = adapter.search("students", filters={"cohort": {"eq": "A1"}})
    assert len(result["rows"]) == 3
    assert all(r["cohort"] == "A1" for r in result["rows"])


def test_search_with_columns(adapter):
    result = adapter.search("students", columns=["name", "score"])
    assert set(result["rows"][0].keys()) == {"name", "score"}


def test_search_with_order(adapter):
    result = adapter.search("students", order_by="score", descending=True)
    scores = [r["score"] for r in result["rows"]]
    assert scores == sorted(scores, reverse=True)


def test_search_invalid_table(adapter):
    with pytest.raises(ValidationError, match="Unknown table"):
        adapter.search("nonexistent")


def test_search_invalid_column(adapter):
    with pytest.raises(ValidationError, match="Unknown column"):
        adapter.search("students", columns=["invalid_col"])


def test_search_invalid_operator(adapter):
    with pytest.raises(ValidationError, match="Unsupported operator"):
        adapter.search("students", filters={"name": {"contains": "Alice"}})


def test_insert_valid(adapter):
    result = adapter.insert("students", {"name": "Frank", "cohort": "A2", "score": 80.0})
    assert "id" in result
    assert result["inserted"]["name"] == "Frank"
    assert result["inserted"]["cohort"] == "A2"


def test_insert_empty_values(adapter):
    with pytest.raises(ValidationError, match="must not be empty"):
        adapter.insert("students", {})


def test_insert_invalid_column(adapter):
    with pytest.raises(ValidationError, match="Unknown column"):
        adapter.insert("students", {"bad_col": "value"})


def test_aggregate_count(adapter):
    result = adapter.aggregate("students", "count")
    assert result[0]["value"] == 5


def test_aggregate_avg(adapter):
    result = adapter.aggregate("students", "avg", "score")
    assert isinstance(result[0]["value"], float)
    assert 70 < result[0]["value"] < 100


def test_aggregate_sum(adapter):
    result = adapter.aggregate("students", "sum", "score")
    assert result[0]["value"] == pytest.approx(92.5 + 78.0 + 88.5 + 65.0 + 95.0)


def test_aggregate_group_by(adapter):
    result = adapter.aggregate("students", "count", group_by="cohort")
    groups = {r["group"] for r in result}
    assert "A1" in groups and "A2" in groups


def test_aggregate_invalid_metric(adapter):
    with pytest.raises(ValidationError, match="Unsupported metric"):
        adapter.aggregate("students", "variance", "score")


def test_aggregate_missing_column(adapter):
    with pytest.raises(ValidationError, match="column is required"):
        adapter.aggregate("students", "avg")
```

- [ ] **Step 2: Run tests — confirm they ALL FAIL (db.py doesn't exist yet)**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation"
python -m pytest tests/test_server.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'db'` or similar import error.

- [ ] **Step 3: Commit the failing tests**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git add implementation/tests/test_server.py
git commit -m "test: add failing unit tests for SQLiteAdapter"
```

---

## Task 4: Implement SQLiteAdapter (`db.py`)

**Files:**
- Create: `implementation/db.py`

- [ ] **Step 1: Create db.py**

```python
# implementation/db.py
import sqlite3

ALLOWED_OPERATORS = {
    "eq": "=", "ne": "!=", "gt": ">", "lt": "<", "gte": ">=", "lte": "<=", "like": "LIKE"
}
ALLOWED_METRICS = {"count", "avg", "sum", "min", "max"}


class ValidationError(Exception):
    pass


class SQLiteAdapter:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info(\"{table}\")").fetchall()
            return [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "pk": bool(row["pk"]),
                    "notnull": bool(row["notnull"]),
                }
                for row in rows
            ]

    def _validate_table(self, table: str) -> None:
        if table not in self.list_tables():
            raise ValidationError(f"Unknown table: '{table}'")

    def _validate_columns(self, table: str, columns: list[str]) -> None:
        known = {col["name"] for col in self.get_table_schema(table)}
        for col in columns:
            if col not in known:
                raise ValidationError(f"Unknown column '{col}' in table '{table}'")

    def _build_where(self, table: str, filters: dict) -> tuple[str, list]:
        parts = []
        params = []
        for col, condition in filters.items():
            self._validate_columns(table, [col])
            if not isinstance(condition, dict):
                raise ValidationError(f"Filter for '{col}' must be a dict like {{\"eq\": value}}")
            for op, val in condition.items():
                if op not in ALLOWED_OPERATORS:
                    raise ValidationError(
                        f"Unsupported operator '{op}'. Allowed: {sorted(ALLOWED_OPERATORS)}"
                    )
                parts.append(f"{col} {ALLOWED_OPERATORS[op]} ?")
                params.append(val)
        return (" AND ".join(parts), params)

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: dict | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict:
        self._validate_table(table)

        if columns:
            self._validate_columns(table, columns)
            col_clause = ", ".join(columns)
        else:
            col_clause = "*"

        params: list = []
        sql = f"SELECT {col_clause} FROM {table}"

        if filters:
            where_clause, where_params = self._build_where(table, filters)
            sql += f" WHERE {where_clause}"
            params.extend(where_params)

        if order_by:
            self._validate_columns(table, [order_by])
            direction = "DESC" if descending else "ASC"
            sql += f" ORDER BY {order_by} {direction}"

        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return {"rows": [dict(r) for r in rows], "count": len(rows), "table": table}

    def insert(self, table: str, values: dict) -> dict:
        self._validate_table(table)
        if not values:
            raise ValidationError("values must not be empty")
        self._validate_columns(table, list(values.keys()))

        cols = ", ".join(values.keys())
        placeholders = ", ".join(["?"] * len(values))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

        with self.connect() as conn:
            cursor = conn.execute(sql, list(values.values()))
            conn.commit()
            row_id = cursor.lastrowid
            row = conn.execute(
                f"SELECT * FROM {table} WHERE rowid = ?", [row_id]
            ).fetchone()
            return {"inserted": dict(row), "id": row_id}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: dict | None = None,
        group_by: str | None = None,
    ) -> list[dict]:
        if metric not in ALLOWED_METRICS:
            raise ValidationError(
                f"Unsupported metric '{metric}'. Allowed: {sorted(ALLOWED_METRICS)}"
            )
        self._validate_table(table)

        if metric != "count" and column is None:
            raise ValidationError(f"column is required for metric '{metric}'")

        if column:
            self._validate_columns(table, [column])
            agg_expr = f"{metric.upper()}({column})"
        else:
            agg_expr = "COUNT(*)"

        params: list = []

        if group_by:
            self._validate_columns(table, [group_by])
            sql = f"SELECT {group_by}, {agg_expr} AS value FROM {table}"
        else:
            sql = f"SELECT {agg_expr} AS value FROM {table}"

        if filters:
            where_clause, where_params = self._build_where(table, filters)
            sql += f" WHERE {where_clause}"
            params.extend(where_params)

        if group_by:
            sql += f" GROUP BY {group_by}"

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            if group_by:
                return [{"group": row[0], "value": row[1]} for row in rows]
            return [{"value": rows[0][0]}] if rows else [{"value": None}]
```

- [ ] **Step 2: Run tests — confirm ALL PASS**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation"
python -m pytest tests/test_server.py -v
```

Expected: all tests PASS, 0 failures.

- [ ] **Step 3: Commit**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git add implementation/db.py
git commit -m "feat: implement SQLiteAdapter with search, insert, aggregate and validation"
```

---

## Task 5: Implement MCP Server (`mcp_server.py`)

**Files:**
- Create: `implementation/mcp_server.py`

- [ ] **Step 1: Create mcp_server.py**

```python
# implementation/mcp_server.py
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP
from db import SQLiteAdapter, ValidationError
from init_db import create_database

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab.db")

if not os.path.exists(DB_PATH):
    create_database(DB_PATH)

mcp = FastMCP("SQLite Lab MCP Server")
adapter = SQLiteAdapter(DB_PATH)


@mcp.tool()
def search(
    table: str,
    columns: list[str] | None = None,
    filters: dict | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict:
    """
    Search rows in a table.

    filters format: {"column": {"op": value}} where op is one of:
      eq, ne, gt, lt, gte, lte, like

    Pagination: use limit (default 20) and offset (default 0).
    """
    try:
        return adapter.search(table, columns, filters, limit, offset, order_by, descending)
    except ValidationError as e:
        return {"error": str(e)}


@mcp.tool()
def insert(table: str, values: dict) -> dict:
    """
    Insert a single row into a table.

    values is a dict mapping column names to values, e.g.:
      {"name": "Alice", "cohort": "A1", "score": 92.5}

    Returns the inserted row plus the generated id.
    """
    try:
        return adapter.insert(table, values)
    except ValidationError as e:
        return {"error": str(e)}


@mcp.tool()
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: dict | None = None,
    group_by: str | None = None,
) -> list:
    """
    Run an aggregate query.

    metric: count | avg | sum | min | max
    column: required for avg, sum, min, max; optional for count
    group_by: optional column name to group results by
    filters: same format as search filters
    """
    try:
        return adapter.aggregate(table, metric, column, filters, group_by)
    except ValidationError as e:
        return [{"error": str(e)}]


@mcp.resource("schema://database")
def database_schema() -> str:
    """Full schema for all tables in the database."""
    tables = adapter.list_tables()
    schema = {table: adapter.get_table_schema(table) for table in tables}
    return json.dumps({"tables": schema}, indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Schema for a single named table."""
    if table_name not in adapter.list_tables():
        return json.dumps({"error": f"Unknown table: '{table_name}'"})
    columns = adapter.get_table_schema(table_name)
    return json.dumps({"table": table_name, "columns": columns}, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite Lab MCP Server")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "http"],
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP/SSE (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE (default: 8000)")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
```

- [ ] **Step 2: Test server starts without error**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation"
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}' | python mcp_server.py
```

Expected: JSON response with `"result"` containing server info (press Ctrl+C if it hangs waiting for input, that's normal for stdio).

- [ ] **Step 3: Commit**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git add implementation/mcp_server.py
git commit -m "feat: implement FastMCP server with search, insert, aggregate tools and schema resources"
```

---

## Task 6: Implement Smoke Test (`verify_server.py`)

**Files:**
- Create: `implementation/verify_server.py`

- [ ] **Step 1: Create verify_server.py**

```python
# implementation/verify_server.py
"""
Headless smoke test for the MCP server.
Run: python verify_server.py
Exits 0 on success, 1 on any failure.
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
PYTHON = sys.executable


def parse(result) -> dict | list:
    if not result.content:
        return {}
    text = result.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


async def verify():
    params = StdioServerParameters(command=PYTHON, args=[SERVER_PATH])
    failures = []

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Tool discovery
            tools_result = await session.list_tools()
            tool_names = {t.name for t in tools_result.tools}
            expected_tools = {"search", "insert", "aggregate"}
            if not expected_tools.issubset(tool_names):
                failures.append(f"Missing tools: {expected_tools - tool_names}")
            else:
                print(f"[PASS] Tools discovered: {sorted(tool_names)}")

            # 2. Resource discovery
            res_result = await session.list_resources()
            uris = {str(r.uri) for r in res_result.resources}
            if "schema://database" not in uris:
                failures.append(f"Missing resource schema://database, got: {uris}")
            else:
                print(f"[PASS] Resource schema://database found")

            # 3. Search students
            r = await session.call_tool("search", {"table": "students"})
            data = parse(r)
            if "rows" not in data or len(data["rows"]) == 0:
                failures.append(f"search(students) expected rows, got: {data}")
            else:
                print(f"[PASS] search(students) -> {len(data['rows'])} rows")

            # 4. Insert student
            r = await session.call_tool("insert", {
                "table": "students",
                "values": {"name": "Verify Bot", "cohort": "A1", "score": 99.0},
            })
            data = parse(r)
            if "id" not in data:
                failures.append(f"insert(students) expected id, got: {data}")
            else:
                print(f"[PASS] insert(students) -> id={data['id']}")

            # 5. Aggregate avg score
            r = await session.call_tool("aggregate", {
                "table": "students",
                "metric": "avg",
                "column": "score",
            })
            data = parse(r)
            rows = data if isinstance(data, list) else [data]
            if not rows or "value" not in rows[0]:
                failures.append(f"aggregate avg score expected value, got: {data}")
            else:
                print(f"[PASS] aggregate(avg score) -> {rows[0]['value']:.1f}")

            # 6. Invalid table → error
            r = await session.call_tool("search", {"table": "nonexistent_table"})
            data = parse(r)
            if "error" not in data:
                failures.append(f"search(nonexistent_table) expected error, got: {data}")
            else:
                print(f"[PASS] search(nonexistent_table) -> error: {data['error']}")

            # 7. Schema resource
            r = await session.read_resource("schema://database")
            content = r.contents[0].text if r.contents else ""
            schema = json.loads(content) if content else {}
            if "tables" not in schema or "students" not in schema["tables"]:
                failures.append(f"schema://database missing expected content, got: {content[:200]}")
            else:
                print(f"[PASS] schema://database -> {list(schema['tables'].keys())}")

    if failures:
        print("\n[FAIL] Some checks failed:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("\n[PASS] All 7 checks passed!")


if __name__ == "__main__":
    asyncio.run(verify())
```

- [ ] **Step 2: Run verify_server.py**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation"
python verify_server.py
```

Expected output:
```
[PASS] Tools discovered: ['aggregate', 'insert', 'search']
[PASS] Resource schema://database found
[PASS] search(students) -> 5 rows
[PASS] insert(students) -> id=6
[PASS] aggregate(avg score) -> 83.6
[PASS] search(nonexistent_table) -> error: Unknown table: 'nonexistent_table'
[PASS] schema://database -> ['students', 'courses', 'enrollments']

[PASS] All 7 checks passed!
```

- [ ] **Step 3: Commit**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git add implementation/verify_server.py
git commit -m "feat: add verify_server smoke test covering all tools and resources"
```

---

## Task 7: Client Configuration and Inspector Scripts

**Files:**
- Create: `implementation/.mcp.json`
- Create: `implementation/start_inspector.sh`
- Create: `implementation/start_inspector.bat`

- [ ] **Step 1: Create .mcp.json**

Replace `ABSOLUTE_PATH_TO_IMPLEMENTATION` with the actual absolute path to the `implementation/` folder.

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "C:/Users/LONG NGO/AppData/Local/Programs/Python/Python312/python.exe",
      "args": ["e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"],
      "env": {}
    }
  }
}
```

- [ ] **Step 2: Create start_inspector.sh (for Git Bash / WSL)**

```bash
#!/bin/bash
# Run MCP Inspector against the SQLite Lab server
# Usage: bash start_inspector.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python)"

mkdir -p "$SCRIPT_DIR/.npm-cache"
NPM_CONFIG_CACHE="$SCRIPT_DIR/.npm-cache" npx -y @modelcontextprotocol/inspector \
  "$PYTHON" "$SCRIPT_DIR/mcp_server.py"
```

- [ ] **Step 3: Create start_inspector.bat (for Windows CMD)**

```bat
@echo off
REM Run MCP Inspector against the SQLite Lab server
REM Usage: start_inspector.bat

set SCRIPT_DIR=%~dp0
set PYTHON=C:\Users\LONG NGO\AppData\Local\Programs\Python\Python312\python.exe

if not exist "%SCRIPT_DIR%.npm-cache" mkdir "%SCRIPT_DIR%.npm-cache"
set NPM_CONFIG_CACHE=%SCRIPT_DIR%.npm-cache
npx -y @modelcontextprotocol/inspector "%PYTHON%" "%SCRIPT_DIR%mcp_server.py"
```

- [ ] **Step 4: Commit**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git add implementation/.mcp.json implementation/start_inspector.sh implementation/start_inspector.bat
git commit -m "feat: add Claude Code .mcp.json config and MCP Inspector launch scripts"
```

---

## Task 8: README

**Files:**
- Modify: `README.md` (top-level, already exists — add Setup and Demo sections)

- [ ] **Step 1: Append setup and demo content to existing README.md**

Open `e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/README.md` and append this section after the existing content:

```markdown

---

## Setup

### Prerequisites
- Python 3.12+
- Node.js 18+ (for MCP Inspector)
- fastmcp already installed: `pip install fastmcp`

### Install dependencies

```bash
pip install fastmcp pytest
```

### Initialize the database

```bash
cd implementation
python init_db.py
```

### Run the server (stdio — for use with Claude Code or Inspector)

```bash
cd implementation
python mcp_server.py
```

### Run HTTP/SSE mode (bonus)

```bash
cd implementation
python mcp_server.py --transport sse --port 8000
```

---

## Testing

### Unit tests

```bash
cd implementation
python -m pytest tests/test_server.py -v
```

### Smoke test (headless MCP client)

```bash
cd implementation
python verify_server.py
```

---

## MCP Inspector

### Windows (CMD)

```bat
cd implementation
start_inspector.bat
```

### Git Bash / WSL

```bash
cd implementation
bash start_inspector.sh
```

Then open the URL shown in the terminal (usually http://localhost:5173).

**Checklist in Inspector:**
- Tools tab: `search`, `insert`, `aggregate` are listed with schemas
- Resources tab: `schema://database` is listed
- Call `search` with `{"table": "students"}` → rows returned
- Call `search` with `{"table": "bad_table"}` → error returned

---

## Claude Code Client

Copy `.mcp.json` from `implementation/.mcp.json` to the project root, or add the server to your Claude Code config:

```bash
claude mcp add sqlite-lab \
  "C:/Users/LONG NGO/AppData/Local/Programs/Python/Python312/python.exe" \
  "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"
```

Then in Claude Code, reference the schema resource with:
```
@sqlite-lab:schema://database
```

### Example prompts

- "Use sqlite-lab to search all students in cohort A1"
- "Use sqlite-lab to insert a new student named Grace in cohort A2 with score 91"
- "Use sqlite-lab to compute average score by cohort"
- "Read @sqlite-lab:schema://table/students and describe the columns"

---

## Demo Tasks

| Task | Tool | Expected |
|------|------|----------|
| List all students | `search` `table=students` | 5 rows |
| Filter cohort A1 | `search` `filters={"cohort":{"eq":"A1"}}` | 3 rows |
| Insert student | `insert` `table=students values={...}` | `{id: N, inserted: {...}}` |
| Count students | `aggregate` `metric=count` | `[{"value": 5}]` |
| Avg score by cohort | `aggregate` `metric=avg column=score group_by=cohort` | 2 groups |
| Bad table | `search` `table=nonexistent` | `{"error": "Unknown table..."}` |
| Read schema | resource `schema://database` | JSON schema |
| Single table schema | resource `schema://table/students` | columns list |
```

- [ ] **Step 2: Commit**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git add README.md
git commit -m "docs: add setup, testing, inspector, and demo sections to README"
```

---

## Task 9: Bonus — HTTP/SSE Transport Verification

**Files:**
- No new files — `mcp_server.py` already supports `--transport sse`

- [ ] **Step 1: Test SSE mode starts successfully**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation"
python mcp_server.py --transport sse --port 8001
```

Expected: Server starts, prints something like `Uvicorn running on http://0.0.0.0:8001`. Press Ctrl+C to stop.

- [ ] **Step 2: Test HTTP streamable mode**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation"
python mcp_server.py --transport http --port 8002
```

Expected: Server starts on port 8002. Press Ctrl+C to stop.

- [ ] **Step 3: Commit**

```bash
cd "e:/Track_3/Day26/Day26-Track3-MCP-tool-integration"
git commit -m "feat: confirm SSE and HTTP transport modes work (bonus)"
```

---

## Self-Review: Spec Coverage Check

| Spec Requirement | Covered By Task |
|------------------|----------------|
| FastMCP server starts | Task 5 Step 2 |
| `search` tool | Task 5 (mcp_server.py) |
| `insert` tool | Task 5 (mcp_server.py) |
| `aggregate` tool | Task 5 (mcp_server.py) |
| `schema://database` resource | Task 5 (mcp_server.py) |
| `schema://table/{table_name}` resource | Task 5 (mcp_server.py) |
| Table/column validation | Task 4 (db.py `_validate_table`, `_validate_columns`) |
| Operator validation | Task 4 (db.py `_build_where`) |
| Parameterized SQL | Task 4 (db.py — `?` placeholders throughout) |
| Empty insert rejection | Task 4 (db.py `insert`) |
| Tool discovery verification | Task 6 (verify_server.py check 1) |
| Valid calls demonstration | Task 6 (checks 3-5) |
| Invalid calls demonstration | Task 6 (check 6) |
| Claude Code client config | Task 7 (.mcp.json) |
| MCP Inspector setup | Task 7 (start_inspector.sh/.bat) |
| README with setup + test steps | Task 8 |
| HTTP/SSE bonus | Task 9 |
| SQLite seed data | Task 2 (init_db.py) |
| Reproducible schema | Task 2 (`CREATE TABLE IF NOT EXISTS`) |
| Pytest unit tests | Task 3-4 (test_server.py, 15 tests) |
