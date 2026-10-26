import sys

from .config import MAX_ROWS
from .graph import build_graph


def main() -> None:
    graph = build_graph()
    history: list[dict] = []
    print("SQL ajanı hazır. Çıkış: boş satır / Ctrl+C")
    while True:
        try:
            q = input("\nSoru> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        out = graph.invoke({"question": q, "history": history})
        history.append({"q": out["standalone"], "sql": out.get("sql", "")})
        print(f"\nSQL ({out['attempts']} deneme, {out['tokens']} token):\n{out.get('sql', '')}\n")
        print(out["answer"])
        if out.get("truncated"):
            print(f"\n({MAX_ROWS}+ satır, ilk {MAX_ROWS} gösteriliyor)")


if __name__ == "__main__":
    sys.exit(main())
