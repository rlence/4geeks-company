"""Fake cliente Supabase para los tests de Hito 6 Parte 2 (pipeline +
endpoints de reporting). Soporta múltiples schemas/tablas en memoria y la
porción del query builder de postgrest que este pipeline usa (select,
gte, lt, in_, eq, order, limit, upsert). No valida SQL real — solo emula
suficiente superficie para probar la lógica de Python que lo llama.
"""


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeReportingTable:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filters = []
        self._order = None
        self._limit = None
        self._pending_upsert = None

    def select(self, columns: str = "*") -> "FakeReportingTable":
        return self

    def gte(self, column: str, value) -> "FakeReportingTable":
        self._filters.append(lambda r: r.get(column) is not None and r[column] >= value)
        return self

    def lt(self, column: str, value) -> "FakeReportingTable":
        self._filters.append(lambda r: r.get(column) is not None and r[column] < value)
        return self

    def eq(self, column: str, value) -> "FakeReportingTable":
        self._filters.append(lambda r: r.get(column) == value)
        return self

    def in_(self, column: str, values: list) -> "FakeReportingTable":
        self._filters.append(lambda r: r.get(column) in values)
        return self

    def order(self, column: str, desc: bool = False) -> "FakeReportingTable":
        self._order = (column, desc)
        return self

    def limit(self, n: int) -> "FakeReportingTable":
        self._limit = n
        return self

    def upsert(self, rows: list[dict], on_conflict: str | None = None, **_kwargs) -> "FakeReportingTable":
        self._pending_upsert = (rows, on_conflict)
        return self

    def execute(self) -> FakeResult:
        if self._pending_upsert is not None:
            rows, on_conflict = self._pending_upsert
            conflict_keys = on_conflict.split(",") if on_conflict else ["id"]
            for row in rows:
                match_index = next(
                    (
                        i
                        for i, existing in enumerate(self._rows)
                        if all(existing.get(k) == row.get(k) for k in conflict_keys)
                    ),
                    None,
                )
                if match_index is not None:
                    self._rows[match_index] = {**self._rows[match_index], **row}
                else:
                    self._rows.append(dict(row))
            self._pending_upsert = None
            return FakeResult(None)

        result = [row for row in self._rows if all(f(row) for f in self._filters)]
        if self._order:
            column, desc = self._order
            result = sorted(result, key=lambda r: r.get(column), reverse=desc)
        if self._limit is not None:
            result = result[: self._limit]
        return FakeResult(result)


class FakeReportingClient:
    """`.table()` opera sobre el schema `public` salvo que se llame
    `.schema("reporting")` primero, igual que el cliente supabase-py real."""

    def __init__(self, tables: dict[tuple[str, str], list[dict]] | None = None):
        self.tables: dict[tuple[str, str], list[dict]] = tables if tables is not None else {}
        self._active_schema = "public"

    def schema(self, name: str) -> "FakeReportingClient":
        scoped = FakeReportingClient(self.tables)
        scoped._active_schema = name
        return scoped

    def table(self, name: str) -> FakeReportingTable:
        key = (self._active_schema, name)
        self.tables.setdefault(key, [])
        return FakeReportingTable(self.tables[key])

    def seed(self, schema: str, table: str, rows: list[dict]) -> None:
        self.tables[(schema, table)] = [dict(row) for row in rows]

    def rows(self, schema: str, table: str) -> list[dict]:
        return self.tables.get((schema, table), [])
