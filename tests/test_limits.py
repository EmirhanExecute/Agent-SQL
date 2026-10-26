from sqlagent import db
from sqlagent import graph as graph_mod
from sqlagent.config import MAX_ROWS, MEMORY_TURNS
from sqlagent.features import DEFAULT, PRESETS, Features
from sqlagent.llm import LLMResult
from sqlagent.security import validate_sql

TABLES = db.list_tables()


def ok(sql):
    return validate_sql(sql, TABLES)


def test_app_always_uses_full_preset_and_five_turns_of_memory():
    assert DEFAULT == PRESETS["full"] and DEFAULT.memory
    assert MEMORY_TURNS == 5


def test_probe_sql_only_when_limit_was_added_or_lowered():
    assert ok("SELECT ProductName FROM Products").probe_sql.endswith("LIMIT 101")
    assert ok("SELECT ProductName FROM Products LIMIT 100000").probe_sql.endswith("LIMIT 101")
    assert ok("SELECT ProductName FROM Products LIMIT 5").probe_sql == ""
    assert "LIMIT 101" in ok("SELECT City FROM Customers UNION SELECT City FROM Suppliers").probe_sql
    assert ok("SELECT ProductName FROM Products").sql.endswith("LIMIT 100")  # what the user sees stays LIMIT 100


def test_run_limited_reports_truncation():
    v = ok('SELECT OrderID, ProductID FROM "Order Details"')  # 269 rows in the small DB
    _, rows, truncated = db.run_limited(v.sql, v.probe_sql)
    assert len(rows) == MAX_ROWS and truncated

    v = ok('SELECT OrderID FROM "Order Details" LIMIT 5')
    _, rows, truncated = db.run_limited(v.sql, v.probe_sql)
    assert len(rows) == 5 and not truncated

    v = ok("SELECT CategoryName FROM Categories")  # 8 rows, limit was added but never reached
    _, rows, truncated = db.run_limited(v.sql, v.probe_sql)
    assert len(rows) == 8 and not truncated


def run_agent(monkeypatch, sql: str):
    """Run the graph with a fake LLM that returns `sql`; returns (final state, prompt given to the answer step)."""
    seen = {}

    def fake_call(messages):
        system, user = messages[0][1], messages[1][1]
        if system.startswith("You are a SQLite expert"):
            return LLMResult(f"```sql\n{sql}\n```", 0, 0.0)
        seen["answer_prompt"] = user
        return LLMResult("ok", 0, 0.0)

    monkeypatch.setattr(graph_mod, "call", fake_call)
    out = graph_mod.build_graph(Features()).invoke({"question": "q", "history": []})
    return out, seen["answer_prompt"]


def test_answer_prompt_says_how_many_rows_are_shown(monkeypatch):
    out, prompt = run_agent(monkeypatch, 'SELECT OrderID, ProductID FROM "Order Details"')
    assert out["truncated"] and len(out["rows"]) == MAX_ROWS
    assert "only the first 20 of 100+ rows" in prompt

    out, prompt = run_agent(monkeypatch, "SELECT ProductName FROM Products LIMIT 30")
    assert not out["truncated"]
    assert "only the first 20 of 30 rows" in prompt

    out, prompt = run_agent(monkeypatch, "SELECT CategoryName FROM Categories")
    assert "Note:" not in prompt


def test_rewrite_uses_only_the_last_five_turns(monkeypatch):
    seen = []

    def fake_call(messages):
        seen.append(messages)
        return LLMResult("standalone question", 0, 0.0)

    monkeypatch.setattr(graph_mod, "call", fake_call)
    history = [{"q": f"q{i}", "sql": f"s{i}"} for i in range(8)]
    for update in graph_mod.build_graph().stream({"question": "follow-up", "history": history}, stream_mode="updates"):
        if "rewrite" in update:  # the rewrite step is the first LLM call; stop before the rest of the pipeline
            break
    prompt = seen[0][1][1]
    assert "Q: q3" in prompt and "Q: q7" in prompt and "Q: q2" not in prompt
