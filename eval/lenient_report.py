"""Post-hoc check: how many 'wrong result' answers differ from the gold result only by EXTRA columns?

The main metric (run_eval.py) requires the same set of columns. Some models helpfully add columns (a COUNT next to a
name, a price next to a product). This script re-runs the saved SQL and counts a result as correct when it contains
every gold row's values plus anything extra, with the same number of rows.

python eval/lenient_report.py eval/results/<claude-run>.json eval/results/<gemini-run>.json
"""
import json
import math
import sqlite3
import sys
from pathlib import Path

import yaml

sys.path.insert(0, "eval")
_argv, sys.argv = sys.argv, sys.argv[:1]  # run_eval parses argv at import time
from run_eval import gold_rows, norm_row  # noqa: E402

DB = "data/northwind_small.db"
QUESTIONS = {q["id"]: q for q in yaml.safe_load(Path("eval/questions.yaml").read_text(encoding="utf-8"))}


def agent_rows(sql: str):
    con = sqlite3.connect(f"file:{Path(DB).resolve().as_posix()}?mode=ro", uri=True)
    try:
        return con.execute(sql).fetchall()
    except sqlite3.Error:
        return None


def contains(agent_row, gold_row) -> bool:
    (gold_s, gold_n), (agent_s, agent_n) = norm_row(gold_row), norm_row(agent_row)
    agent_s, agent_n = list(agent_s), list(agent_n)
    for s in gold_s:
        if s not in agent_s:
            return False
        agent_s.remove(s)
    for x in gold_n:
        hit = next((y for y in agent_n if math.isclose(x, y, rel_tol=1e-3, abs_tol=0.01)), None)
        if hit is None:
            return False
        agent_n.remove(hit)
    return True


def lenient_match(agent, gold) -> bool:
    if agent is None or len(agent) != len(gold):
        return False
    used: set[int] = set()
    for g in gold:
        j = next((i for i, a in enumerate(agent) if i not in used and contains(a, g)), None)
        if j is None:
            return False
        used.add(j)
    return True


def is_sql(sql: str) -> bool:
    return sql.lstrip().upper().startswith(("SELECT", "WITH"))


def report(path: str) -> None:
    details = json.loads(Path(path).read_text(encoding="utf-8"))
    print(f"\n== {path}")
    for cfg, results in details.items():
        strict = sum(r["correct"] for r in results)
        extra_only, still_wrong = [], []
        for r in results:
            q = QUESTIONS[r["id"]]
            if r["correct"]:
                continue
            if q.get("expect", "sql") == "sql" and is_sql(r["sql"]) and lenient_match(agent_rows(r["sql"]), gold_rows(DB, q["sql"])):
                extra_only.append(r["id"])
            else:
                still_wrong.append(r["id"])
        print(f"{cfg:<9} strict {strict}/{len(results)} | extra columns only: {len(extra_only)} "
              f"| lenient {strict + len(extra_only)}/{len(results)} | still wrong: {still_wrong}")


if __name__ == "__main__":
    for p in _argv[1:]:
        report(p)
