from typing import TypedDict


class AgentState(TypedDict, total=False):
    question: str            # as typed by the user
    history: list[dict]      # previous turns: [{"q": ..., "sql": ...}]
    standalone: str          # question after follow-up rewriting
    tables: list[str]
    schema: str
    hints: list[str]
    examples: list[dict]
    sql: str
    error: str
    blocked: bool
    attempts: int
    columns: list[str]
    rows: list[tuple]
    answer: str
    tokens: int
    llm_seconds: float
    llm_calls: int
