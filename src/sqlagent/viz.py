"""Rule-based chart selection (deliberately not LLM-driven: deterministic and testable)."""
import re
from dataclasses import dataclass

MAX_BARS = 30
DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?")


@dataclass
class ChartSpec:
    kind: str            # "bar" | "line" | "none"
    x: str = ""
    ys: tuple[str, ...] = ()
    reason: str = ""     # code explaining why there is no chart: min_size | first_col | no_numeric | too_many


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _col_is_numeric(rows, i: int) -> bool:
    vals = [r[i] for r in rows if r[i] is not None]
    return bool(vals) and all(_is_num(v) for v in vals)


def choose_chart(columns: list[str], rows: list[tuple]) -> ChartSpec:
    if len(rows) < 2 or len(columns) < 2:
        return ChartSpec("none", reason="min_size")
    numeric = [_col_is_numeric(rows, i) for i in range(len(columns))]
    first_is_id = numeric[0] and columns[0].lower().endswith("id")
    if numeric[0] and not first_is_id:
        return ChartSpec("none", reason="first_col")
    ys = tuple(c for i, c in enumerate(columns) if i > 0 and numeric[i])[:3]
    if not ys:
        return ChartSpec("none", reason="no_numeric")
    x = columns[0]
    if not numeric[0] and all(isinstance(r[0], str) and DATE_RE.match(r[0]) for r in rows if r[0] is not None):
        return ChartSpec("line", x, ys)
    if len(rows) > MAX_BARS:
        return ChartSpec("none", reason="too_many")
    return ChartSpec("bar", x, ys)
