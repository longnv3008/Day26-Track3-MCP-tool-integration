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
