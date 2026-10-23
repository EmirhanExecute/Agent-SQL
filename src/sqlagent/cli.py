import argparse
import sys

from .features import PRESETS
from .graph import build_graph


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="full", choices=PRESETS)
    args = ap.parse_args()
    graph = build_graph(PRESETS[args.preset])
    history: list[dict] = []
    print(f"SQL ajanı hazır (preset={args.preset}). Çıkış: boş satır / Ctrl+C")
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


if __name__ == "__main__":
    sys.exit(main())
