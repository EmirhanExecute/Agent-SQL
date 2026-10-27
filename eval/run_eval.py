"""Execution-accuracy evaluation / ablation.

python eval/run_eval.py --db small --split test --configs baseline,fewshot,repair,values,tables
Env: LLM_CACHE=1 caches LLM calls on disk; LLM_CACHE_SALT=<x> forces fresh samples (use for --repeat runs).
"""
import argparse
import json
import math
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, "src")
os.environ.setdefault("LLM_CACHE", "1")

# --provider / --model must be applied before sqlagent is imported (config reads the environment at import time)
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--provider")
_pre.add_argument("--model")
_known, _ = _pre.parse_known_args()
if _known.provider:
    os.environ["LLM_PROVIDER"] = _known.provider
if _known.model:
    os.environ["MODEL_NAME"] = _known.model

from sqlagent.config import MODEL_NAME, PROVIDER  # noqa: E402
from sqlagent.features import PRESETS  # noqa: E402
from sqlagent.graph import build_graph  # noqa: E402

LEVELS = ["easy", "medium", "hard", "unanswerable", "ambiguous"]
ACCEPTED = {"cannot_answer": {"cannot_answer"}, "clarify": {"clarify"}}


def norm_row(r) -> tuple[tuple, tuple]:
    """Split a row into (sorted text cells, sorted numeric cells) so column order does not matter."""
    strs = sorted(str(c).strip().lower() for c in r if c is not None and not isinstance(c, (int, float)))
    nums = sorted(float(c) for c in r if isinstance(c, (int, float)) and not isinstance(c, bool))
    return tuple(strs), tuple(nums)


def same_result(a, b) -> bool:
    """Order-insensitive in rows and columns; numbers equal within abs 0.01 / rel 0.1% (rounding differences)."""
    ra, rb = sorted(map(norm_row, a)), sorted(map(norm_row, b))
    if len(ra) != len(rb):
        return False
    return all(x[0] == y[0] and len(x[1]) == len(y[1]) and all(math.isclose(p, q, rel_tol=1e-3, abs_tol=0.01)
                                                                  for p, q in zip(x[1], y[1]))
               for x, y in zip(ra, rb))


def gold_rows(db_path: str, sql: str):
    with sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True) as c:
        return c.execute(sql).fetchall()


def run_one(graph, q: dict, db_path: str) -> dict:
    t0 = time.perf_counter()
    try:
        out = graph.invoke({"question": q["q"], "history": []})
        err = out.get("error", "")
        expect = q.get("expect", "sql")
        if expect == "sql":
            correct = (not out.get("abstain")) and (not err) and same_result(out.get("rows", []), gold_rows(db_path, q["sql"]))
        else:  # must abstain in the expected way and never execute SQL; a security block also counts as refusing
            kind = out.get("abstain") or ("cannot_answer" if out.get("blocked") else "")
            correct = kind in ACCEPTED[expect] and not out.get("rows")
        return {"id": q["id"], "level": q["level"], "correct": bool(correct), "sql": out.get("sql", "") or out.get("answer", ""),
                "error": err, "attempts": out.get("attempts", 0), "tokens": out.get("tokens", 0),
                "llm_seconds": out.get("llm_seconds", 0.0), "wall_seconds": time.perf_counter() - t0}
    except Exception as e:
        return {"id": q["id"], "level": q["level"], "correct": False, "sql": "", "error": f"CRASH {e!r}",
                "attempts": 0, "tokens": 0, "llm_seconds": 0.0, "wall_seconds": time.perf_counter() - t0}


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(p * len(xs)) - 1)] if xs else 0.0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def summarize(name: str, rs: list[dict]) -> dict:
    n, k = len(rs), sum(r["correct"] for r in rs)
    lo, hi = wilson(k, n)
    by = {lv: (sum(r["correct"] for r in rs if r["level"] == lv), sum(r["level"] == lv for r in rs)) for lv in LEVELS}
    return {"config": name, "n": n, "correct": k, "acc": k / n, "ci": (lo, hi), "by_level": by,
            "tokens": sum(r["tokens"] for r in rs) / n, "attempts": sum(r["attempts"] for r in rs) / n,
            "p50": pct([r["llm_seconds"] for r in rs], 0.5), "p95": pct([r["llm_seconds"] for r in rs], 0.95)}


def print_table(summaries: list[dict], title: str) -> str:
    lines = [f"### {title}", "",
             "| Config | Execution accuracy (95% CI) | easy | medium | hard | unanswerable | ambiguous | tokens/q | attempts/q | LLM s p50 | p95 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        lv = " | ".join(f"{a}/{b}" for a, b in (s["by_level"][l] for l in LEVELS))
        lines.append(f"| {s['config']} | {s['acc']:.0%} ({s['correct']}/{s['n']}; {s['ci'][0]:.0%}-{s['ci'][1]:.0%}) | {lv} "
                     f"| {s['tokens']:.0f} | {s['attempts']:.2f} | {s['p50']:.1f} | {s['p95']:.1f} |")
    text = "\n".join(lines)
    print("\n" + text)
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="small", choices=["small", "full", "poisoned"])
    ap.add_argument("--split", default="test", choices=["test", "train", "all"])
    ap.add_argument("--configs", default="baseline,fewshot,repair,values,tables")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default="", help="comma-separated question ids")
    ap.add_argument("--provider", help="gemini | anthropic (default: LLM_PROVIDER env, else gemini)")
    ap.add_argument("--model", help="model name (default: provider's default, or MODEL_NAME env)")
    args = ap.parse_args()

    db_path = f"data/northwind_{args.db}.db"
    qs = yaml.safe_load(Path("eval/questions.yaml").read_text(encoding="utf-8"))
    if args.split != "all":
        qs = [q for q in qs if q["split"] == args.split]
    if args.only:
        qs = [q for q in qs if q["id"] in args.only.split(",")]

    summaries, details = [], {}
    for name in args.configs.split(","):
        graph = build_graph(PRESETS[name], with_answer=False, db_path=db_path)
        with ThreadPoolExecutor(args.workers) as ex:
            def task(q, name=name):
                r = run_one(graph, q, db_path)
                print(f"  [{args.db}/{name}] {r['id']} {'ok' if r['correct'] else 'FAIL'} ({r['wall_seconds']:.0f}s)", flush=True)
                return r
            rs = list(ex.map(task, qs))
        details[name] = rs
        summaries.append(summarize(name, rs))
        s = summaries[-1]
        print(f"{name:<10} {s['correct']}/{s['n']}  tokens/q={s['tokens']:.0f}  attempts/q={s['attempts']:.2f}", flush=True)

    table = print_table(summaries, f"{args.db} DB, {args.split} split, {len(qs)} questions, {PROVIDER}:{MODEL_NAME}")
    out_dir = Path("eval/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    tag = f"{args.db}-{PROVIDER}"
    (out_dir / f"{stamp}-{tag}.json").write_text(json.dumps(details, indent=1, ensure_ascii=False), encoding="utf-8")
    (out_dir / f"{stamp}-{tag}.md").write_text(table, encoding="utf-8")
    fails = [(n, r) for n, rs in details.items() for r in rs if not r["correct"] and n == args.configs.split(",")[-1]]
    for n, r in fails[:15]:
        print(f"[{n}] FAIL {r['id']}: {r['error'] or 'wrong result'}\n     {r['sql'][:200]}")


if __name__ == "__main__":
    main()
