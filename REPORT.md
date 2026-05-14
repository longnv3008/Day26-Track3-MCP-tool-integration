# Báo Cáo Cá Nhân — Day 26: MCP Tool Integration

**Họ và tên:** Ngô Văn Long  
**Mã học viên:** 2A202600129  
**Repository:** https://github.com/longnv3008/Day26-Track3-MCP-tool-integration  
**Ngày nộp:** 2026-05-14

---

## 1. Tổng Quan Dự Án

Xây dựng một **FastMCP server** kết nối với **SQLite** để expose dữ liệu sinh viên thông qua Model Context Protocol (MCP). Server hỗ trợ ba công cụ (`search`, `insert`, `aggregate`), hai resource schema, validation an toàn, và có thể kết nối với Claude Code hoặc MCP Inspector.

---

## 2. Kiến Trúc Dự Án

```
implementation/
├── db.py              # Tầng cơ sở dữ liệu: SQLiteAdapter + ValidationError
├── init_db.py         # Khởi tạo schema và seed data
├── mcp_server.py      # FastMCP server: 3 tools + 2 resources
├── verify_server.py   # Smoke test headless qua MCP Python client
├── .mcp.json          # Cấu hình Claude Code client
├── start_inspector.sh # Script chạy MCP Inspector (Linux/Mac)
├── start_inspector.bat# Script chạy MCP Inspector (Windows)
├── requirements.txt   # Dependencies
└── tests/
    └── test_server.py # 18 unit tests cho SQLiteAdapter
```

**Quyết định thiết kế chính:**
- Tách `db.py` (logic DB thuần) và `mcp_server.py` (FastMCP decorators) để dễ test và bảo trì
- Validation qua whitelist (không concat SQL trực tiếp) — an toàn theo OWASP
- Filters dùng format `{"column": {"op": value}}` — rõ ràng và dễ mở rộng
- `verify_server.py` chạy headless qua MCP Python client — không cần MCP Inspector

---

## 3. Schema Cơ Sở Dữ Liệu

Sử dụng bộ dữ liệu quan hệ nhỏ gồm 3 bảng:

| Bảng | Cột | Ghi chú |
|------|-----|---------|
| `students` | id, name, cohort, score | 5 sinh viên seed |
| `courses` | id, title, credits | 3 khóa học seed |
| `enrollments` | id, student_id, course_id, grade | 6 enrollment seed |

Schema sử dụng `CREATE TABLE IF NOT EXISTS` và `INSERT OR IGNORE` để đảm bảo tính idempotent.

---

## 4. Công Cụ MCP Đã Implement

### `search` — Tìm kiếm dữ liệu
```json
{
  "table": "students",
  "columns": ["name", "score"],
  "filters": {"cohort": {"eq": "A1"}},
  "order_by": "score",
  "descending": true,
  "limit": 10,
  "offset": 0
}
```
- Hỗ trợ toán tử: `eq`, `ne`, `gt`, `lt`, `gte`, `lte`, `like`
- Projection (chọn cột), sắp xếp, phân trang

### `insert` — Thêm dòng mới
```json
{
  "table": "students",
  "values": {"name": "Grace", "cohort": "A2", "score": 91.0}
}
```
- Trả về `{"inserted": {...}, "id": N}`

### `aggregate` — Tính toán thống kê
```json
{
  "table": "students",
  "metric": "avg",
  "column": "score",
  "group_by": "cohort"
}
```
- Metrics: `count`, `avg`, `sum`, `min`, `max`
- Hỗ trợ group by và filters

---

## 5. MCP Resources

| URI | Mô tả |
|-----|-------|
| `schema://database` | Schema đầy đủ của tất cả bảng (JSON) |
| `schema://table/{table_name}` | Schema của một bảng cụ thể |

Trong Claude Code, tham chiếu bằng: `@sqlite-lab:schema://database`

---

## 6. An Toàn và Validation

Tất cả input đều được validate **trước khi** thực thi SQL:

| Loại lỗi | Xử lý |
|----------|-------|
| Tên bảng không tồn tại | `ValidationError("Unknown table: '...'")`  |
| Tên cột không hợp lệ | `ValidationError("Unknown column '...' in table '...'")`  |
| Toán tử filter không hỗ trợ | `ValidationError("Unsupported operator '...'")`  |
| Metric aggregate không hợp lệ | `ValidationError("Unsupported metric '...'")`  |
| Insert với values rỗng | `ValidationError("values must not be empty")`  |

Giá trị người dùng nhập luôn dùng **parameterized query** (`?` placeholder) — không bao giờ concat vào SQL string.

---

## 7. Kết Quả Testing

### Unit Tests (pytest)
```
18 tests passed in 0.21s
```

Các test cover:
- `list_tables`, `get_table_schema`
- `search`: valid, filter, columns, order, invalid table/column/operator
- `insert`: valid, empty values, invalid column
- `aggregate`: count, avg, sum, group_by, invalid metric, missing column

### Smoke Test (verify_server.py)
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

---

## 8. Kết Nối Client

### Claude Code
Cấu hình qua `implementation/.mcp.json`:
```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "C:/Users/LONG NGO/AppData/Local/Programs/Python/Python312/python.exe",
      "args": ["e:/Track_3/Day26/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"]
    }
  }
}
```

Hoặc dùng CLI:
```bash
claude mcp add sqlite-lab python mcp_server.py
```

### MCP Inspector
```bat
cd implementation
start_inspector.bat
```
Mở http://localhost:5173 để xem Tools tab và Resources tab.

---

## 9. Bonus: HTTP/SSE Transport

Server hỗ trợ ba transport mode qua `argparse`:

```bash
python mcp_server.py                          # stdio (mặc định)
python mcp_server.py --transport sse --port 8000   # SSE transport
python mcp_server.py --transport http --port 8000  # HTTP Streamable transport
```

Đã verify cả hai mode SSE và HTTP khởi động thành công với Uvicorn.

---

## 10. Hướng Dẫn Chạy Nhanh

```bash
# Cài dependencies
pip install fastmcp mcp pytest

# Khởi tạo database
cd implementation
python init_db.py

# Chạy unit tests
python -m pytest tests/test_server.py -v

# Chạy smoke test (cần server có thể start)
python verify_server.py

# Chạy server (stdio)
python mcp_server.py
```

---

## 11. Đánh Giá Theo Rubric

| Hạng mục | Điểm tối đa | Ước tính |
|----------|-------------|----------|
| Server Foundation | 20 | 20 |
| Required Tools (search, insert, aggregate) | 30 | 30 |
| MCP Resources | 15 | 15 |
| Safety & Error Handling | 15 | 15 |
| Verification | 10 | 10 |
| Client Integration & Demo | 10 | 9 |
| **Tổng cơ bản** | **100** | **99** |
| Bonus (SSE/HTTP transport) | +5 | +5 |
| **Tổng dự kiến** | **110** | **104** |

---

## 12. Những Điều Học Được

1. **MCP Protocol**: Hiểu cách tool/resource được expose và discover qua JSON-RPC stdio
2. **FastMCP**: Sử dụng `@mcp.tool()` và `@mcp.resource()` decorator để build server nhanh
3. **SQL Safety**: Tầm quan trọng của whitelist validation + parameterized query
4. **TDD Workflow**: Viết test trước (fail), rồi implement để test pass — giúp code đúng spec
5. **MCP Client**: Kết nối headless qua `mcp.ClientSession` + `stdio_client`
6. **Transport Modes**: FastMCP hỗ trợ stdio, SSE, HTTP Streamable thông qua argparse
