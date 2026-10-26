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
    probe_sql: str           # LIMIT max_rows+1 variant used to detect truncation ('' when not applicable)
    truncated: bool          # more than max_rows rows existed; rows holds the first max_rows
    error: str
    blocked: bool
    abstain: str             # '' | 'cannot_answer' | 'clarify'
    attempts: int
    columns: list[str]
    rows: list[tuple]
    answer: str
    tokens: int
    llm_seconds: float
    llm_calls: int
