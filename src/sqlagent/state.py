from typing import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    schema: str
    sql: str
    error: str
    attempts: int
    columns: list[str]
    rows: list[tuple]
    answer: str
    tokens: int
