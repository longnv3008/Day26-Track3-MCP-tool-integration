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
