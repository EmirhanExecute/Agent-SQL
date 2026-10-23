"""Deterministic SQL validation (sqlglot AST). Defence in depth: db.py enforces the same rules at the engine level."""
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from .config import MAX_ROWS
from .policy import DENIED_FUNCTIONS, SENSITIVE_COLUMNS, SENSITIVE_NAMES


@dataclass
class Validation:
    ok: bool
    sql: str = ""        # normalized + LIMIT-enforced SQL when ok
    reason: str = ""     # explanation (fed back to the model for repair) when rejected


def _reject(reason: str) -> Validation:
    return Validation(False, reason=reason)


def validate_sql(sql: str, allowed_tables: list[str], max_rows: int = MAX_ROWS) -> Validation:
    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except sqlglot.errors.ParseError as e:
        return _reject(f"SQL could not be parsed: {e}")
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        return _reject("Exactly one SQL statement is allowed.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.SetOperation)):
        return _reject("Only read-only SELECT queries are allowed.")

    cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    allowed = {t.lower() for t in allowed_tables}
    referenced: set[str] = set()
    for t in tree.find_all(exp.Table):
        name = t.name.lower()
        if name in cte_names:
            continue
        if name not in allowed:
            return _reject(f'Table "{t.name}" does not exist or is not accessible.')
        referenced.add(name)

    for f in tree.find_all(exp.Func):
        fname = (f.name if isinstance(f, exp.Anonymous) else f.sql_name()).lower()
        if fname in DENIED_FUNCTIONS or fname.startswith("pragma_"):
            return _reject(f"Function {fname} is not allowed.")
    for t in tree.find_all(exp.Table):
        if isinstance(t.this, exp.Func):
            return _reject("Table-valued functions are not allowed.")

    for c in tree.find_all(exp.Column):
        if c.name.lower() in SENSITIVE_NAMES:
            return _reject(f'Column "{c.name}" is restricted and cannot be queried.')
    sensitive_tables = {t.lower() for t in SENSITIVE_COLUMNS}
    for star in tree.find_all(exp.Star):
        if isinstance(star.parent, exp.Count):
            continue
        scope = star.find_ancestor(exp.Select)
        scope_tables = {t.name.lower() for t in scope.find_all(exp.Table) if t.find_ancestor(exp.Select) is scope}
        if scope_tables & sensitive_tables:
            return _reject("SELECT * is not allowed on tables with restricted columns; list columns explicitly.")

    limit = tree.args.get("limit")
    current = limit.expression if limit else None
    if not (isinstance(current, exp.Literal) and current.is_int and int(current.name) <= max_rows):
        tree.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
    return Validation(True, sql=tree.sql(dialect="sqlite"))
