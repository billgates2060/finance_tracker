"""In-memory stand-in for the `supabase` package (offline test only)."""
import copy

class _Res:
    def __init__(self, data): self.data = data

class _Q:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.op, self.payload, self.filters = "select", None, []
        self._order, self._range, self._conflict = None, None, None
    def select(self, *_a, **_k): self.op = "select"; return self
    def insert(self, data, **_k): self.op, self.payload = "insert", data; return self
    def update(self, data, **_k): self.op, self.payload = "update", data; return self
    def delete(self, **_k): self.op = "delete"; return self
    def upsert(self, data, on_conflict="", **_k): self.op, self.payload, self._conflict = "upsert", data, on_conflict; return self
    def eq(self, col, val): self.filters.append((col, val)); return self
    def order(self, col, **_k): self._order = col; return self
    def range(self, a, b): self._range = (a, b); return self
    def _match(self, row): return all(str(row.get(c)) == str(v) for c, v in self.filters)
    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "select":
            out = [copy.deepcopy(r) for r in rows if self._match(r)]
            if self._order: out.sort(key=lambda r: (r.get(self._order) is None, r.get(self._order)))
            if self._range: out = out[self._range[0]:self._range[1] + 1]
            return _Res(out)
        if self.op == "insert":
            row = dict(self.payload)
            if self.table in self.db.autoid:
                self.db.seq[self.table] = self.db.seq.get(self.table, 0) + 1
                row["id"] = self.db.seq[self.table]
            for k, v in row.items():   # must be JSON-serialisable like the real client
                import json; json.dumps(v)
            rows.append(row); return _Res([row])
        if self.op == "update":
            import json; json.dumps(self.payload)
            n = 0
            for r in rows:
                if self._match(r): r.update(self.payload); n += 1
            return _Res([{}] * n)
        if self.op == "delete":
            self.db.tables[self.table] = [r for r in rows if not self._match(r)]
            return _Res([])
        if self.op == "upsert":
            import json; json.dumps(self.payload)
            for r in rows:
                if r.get(self._conflict) == self.payload.get(self._conflict):
                    r.update(self.payload); return _Res([r])
            rows.append(dict(self.payload)); return _Res([self.payload])

class FakeClient:
    db_singleton = None
    def __init__(self):
        self.tables, self.seq = {}, {}
        self.autoid = {"income", "expenses", "bills", "goals"}
    def table(self, name): return _Q(self, name)

def create_client(url, key):
    if FakeClient.db_singleton is None:
        FakeClient.db_singleton = FakeClient()
    return FakeClient.db_singleton
