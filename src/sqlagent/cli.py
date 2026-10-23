import sys

from .graph import build_graph


def main() -> None:
    graph = build_graph()
    print("SQL ajanı hazır. Çıkış: boş satır / Ctrl+C")
    while True:
        try:
            q = input("\nSoru> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        out = graph.invoke({"question": q})
        print(f"\nSQL ({out['attempts']} deneme, {out['tokens']} token):\n{out['sql']}\n")
        print(out["answer"])


if __name__ == "__main__":
    sys.exit(main())
