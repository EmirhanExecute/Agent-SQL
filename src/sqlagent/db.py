"""Thin SQLite access layer: read-only connection, schema introspection, query execution."""
import sqlite3
import time
from pathlib import Path

from .config import DB_PATH, MAX_ROWS
from .policy import DENIED_FUNCTIONS, QUERY_TIMEOUT_S, SENSITIVE_COLUMNS, SENSITIVE_NAMES


def connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def connect_hardened(db_path: str = DB_PATH, timeout_s: float = QUERY_TIMEOUT_S) -> sqlite3.Connection:
    """Read-only connection with an engine-level authorizer and a wall-clock timeout."""
    conn = connect(db_path)
    ok, deny = sqlite3.SQLITE_OK, sqlite3.SQLITE_DENY

    def authorizer(action, arg1, arg2, _db, _src):
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
            return ok
        if action == sqlite3.SQLITE_READ:
            # arg1 is empty/CTE name for non-table reads; real tables are checked individually
            if (arg1 or "").lower().startswith("sqlite_") or (arg2 or "").lower() in SENSITIVE_NAMES:
                return deny
            return ok
        if action == sqlite3.SQLITE_FUNCTION:
            return deny if (arg2 or "").lower() in DENIED_FUNCTIONS else ok
        return deny

    conn.set_authorizer(authorizer)
    deadline = time.monotonic() + timeout_s
    conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)
    return conn


def list_tables(db_path: str = DB_PATH) -> list[str]:
    with connect(db_path) as c:
        rows = c.execute(
            "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name"
        ).fetchall()
    return [r[0] for r in rows]


def _fmt(v) -> str:
    if isinstance(v, bytes):
        return f"<blob {len(v)} bytes>"
    s = str(v)
    return s if len(s) <= 40 else s[:37] + "..."


def get_schema(table: str, db_path: str = DB_PATH, n_samples: int = 3) -> str:
    if table not in list_tables(db_path):
        raise ValueError(f"unknown table: {table}")
    with connect(db_path) as c:
        hidden = {h.lower() for h in SENSITIVE_COLUMNS.get(table, ())}
        cols = [r for r in c.execute(f'pragma table_info("{table}")').fetchall() if r[1].lower() not in hidden]
        fks = c.execute(f'pragma foreign_key_list("{table}")').fetchall()
        select_cols = ", ".join(f'"{r[1]}"' for r in cols)
        samples = c.execute(f'select {select_cols} from "{table}" limit {n_samples}').fetchall()
    lines = [f'TABLE "{table}"']
    for _, name, typ, _notnull, _dflt, pk in cols:
        lines.append(f'  - "{name}" {typ or "?"}{" PRIMARY KEY" if pk else ""}')
    for fk in fks:
        lines.append(f'  FK "{fk[3]}" -> "{fk[2]}"."{fk[4]}"')
    if samples:
        lines.append("  sample rows:")
        for row in samples:
            lines.append("    " + " | ".join(_fmt(v) for v in row))
    return "\n".join(lines)


def full_schema(db_path: str = DB_PATH) -> str:
    return "\n\n".join(get_schema(t, db_path) for t in list_tables(db_path))


def run_query(sql: str, db_path: str = DB_PATH, max_rows: int = MAX_ROWS) -> tuple[list[str], list[tuple]]:
    """Execute SQL read-only; returns (columns, rows) capped at max_rows. Raises sqlite3.Error on failure."""
    with connect_hardened(db_path) as c:
        cur = c.execute(sql)
        cols = [d[0] for d in cur.description or []]
        rows = cur.fetchmany(max_rows)
    return cols, rows
