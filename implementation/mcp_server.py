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
