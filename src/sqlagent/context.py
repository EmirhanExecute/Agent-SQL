"""Schema enrichment: categorical value dictionary, business glossary, value linking, table selection helpers."""
import re
from difflib import get_close_matches
from functools import lru_cache

from . import db
from .config import DB_PATH
from .policy import SENSITIVE_COLUMNS

GLOSSARY = """- Dates are TEXT like '1996-07-04 00:00:00.000'; use strftime('%Y-%m', col) / date functions.
- Revenue / sales amount of an order line = UnitPrice * Quantity * (1 - Discount) from "Order Details".
- Products.Discontinued is TEXT: '1' = discontinued, '0' = still sold.
- Orders.ShipVia references Shippers.ShipperID; an order is shipped late when ShippedDate > RequiredDate.
- Employees.ReportsTo references Employees.EmployeeID (the manager)."""

STOPWORDS = {"the", "and", "for", "with", "how", "many", "what", "which", "per", "each", "all", "are", "was", "were",
             "from", "have", "has", "that", "this", "total", "list", "show", "give", "name", "names", "number",
             "kaç", "hangi", "her", "ve", "ile", "için", "olan", "bir", "listele", "göster", "toplam"}


def _text_cols(table: str, db_path: str) -> list[tuple[str, str, bool]]:
    """Visible columns as (name, type, is_key); BLOBs and restricted columns are excluded."""
    hidden = {h.lower() for h in SENSITIVE_COLUMNS.get(table, ())}
    with db.connect(db_path) as c:
        cols = c.execute(f'pragma table_info("{table}")').fetchall()
        fk_cols = {r[3] for r in c.execute(f'pragma foreign_key_list("{table}")').fetchall()}
    return [
        (n, (t or "").upper(), bool(pk) or n in fk_cols)
        for _, n, t, _nn, _d, pk in cols
        if n.lower() not in hidden and "BLOB" not in (t or "").upper()
    ]


@lru_cache(maxsize=None)
def categorical_values(db_path: str, table: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    with db.connect(db_path) as c:
        for name, typ, is_key in _text_cols(table, db_path):
            if is_key or "DATE" in name.upper() or name.lower().endswith("id"):
                continue
            vals = [r[0] for r in c.execute(f'select distinct "{name}" from "{table}" where "{name}" is not null limit 40')]
            limit = 25 if ("CHAR" in typ or "TEXT" in typ) else 8
            if 0 < len(vals) <= limit and all(len(str(v)) <= 40 for v in vals):
                out[name] = sorted(map(str, vals))
    return out


@lru_cache(maxsize=None)
def value_index(db_path: str) -> dict[str, list[tuple[str, str, str]]]:
    """lowercased value -> [(table, column, original value)] for short text columns."""
    idx: dict[str, list[tuple[str, str, str]]] = {}
    with db.connect(db_path) as c:
        for table in db.list_tables(db_path):
            for name, typ, is_key in _text_cols(table, db_path):
                if is_key or not ("CHAR" in typ or "TEXT" in typ):
                    continue
                if any(w in name.lower() for w in ("date", "description", "notes", "picture", "postal")):
                    continue
                for (v,) in c.execute(f'select distinct "{name}" from "{table}" where "{name}" is not null limit 5000'):
                    v = str(v)
                    if 2 < len(v) <= 60:
                        idx.setdefault(v.lower(), []).append((table, name, v))
    return idx


def link_values(question: str, db_path: str = DB_PATH, max_hints: int = 8) -> list[str]:
    idx = value_index(db_path)
    keys = list(idx)
    tokens = re.findall(r"[\w'’/\-]+", question.lower())
    used: set[int] = set()
    hints: list[str] = []
    for n in (3, 2, 1):
        for i in range(len(tokens) - n + 1):
            span = set(range(i, i + n))
            gram = " ".join(tokens[i:i + n]).strip("'’")
            if span & used or len(gram) < 3 or gram in STOPWORDS:
                continue
            match = gram if gram in idx else None
            if not match and len(gram) >= 5:
                close = get_close_matches(gram, keys, n=1, cutoff=0.88)
                match = close[0] if close else None
            if match:
                used |= span
                where = ", ".join(sorted({f"{t}.{c}" for t, c, _ in idx[match]})[:4])
                hints.append(f"'{idx[match][0][2]}' appears as a value in: {where}")
    return hints[:max_hints]


def fk_edges(db_path: str = DB_PATH) -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {t: set() for t in db.list_tables(db_path)}
    with db.connect(db_path) as c:
        for t in list(edges):
            for r in c.execute(f'pragma foreign_key_list("{t}")').fetchall():
                if r[2] in edges:
                    edges[t].add(r[2])
    return edges


def expand_tables(selected: list[str], db_path: str = DB_PATH) -> list[str]:
    """Add junction tables that link two selected tables (e.g. "Order Details" between Orders and Products)."""
    edges = fk_edges(db_path)
    chosen = set(selected)
    for t, targets in edges.items():
        if t not in chosen and len(targets & chosen) >= 2:
            chosen.add(t)
    return sorted(chosen)


def table_overview(db_path: str = DB_PATH) -> str:
    lines = []
    for t in db.list_tables(db_path):
        cols = ", ".join(n for n, _, _ in _text_cols(t, db_path))
        lines.append(f'- "{t}": {cols}')
    return "\n".join(lines)
