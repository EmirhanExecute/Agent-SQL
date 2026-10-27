"""Download the public Northwind SQLite script and build the three databases used by the project.

Run from the repository root:  python scripts/setup_data.py
Creates data/northwind_full.db, data/northwind_small.db and data/northwind_poisoned.db (all git-ignored).
"""
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/main/src/create.sql"
RAW = Path("data/raw/northwind.sql")
FULL = Path("data/northwind_full.db")


def main() -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if not RAW.exists():
        print(f"Downloading {URL}")
        urllib.request.urlretrieve(URL, RAW)
    FULL.unlink(missing_ok=True)
    con = sqlite3.connect(FULL)
    con.executescript(RAW.read_text(encoding="utf-8"))
    con.commit()
    print("full:", con.execute("select count(*) from Orders").fetchone()[0], "orders")
    con.close()
    for script in ("make_small_db.py", "make_poisoned_db.py"):
        subprocess.run([sys.executable, f"scripts/{script}"], check=True)


if __name__ == "__main__":
    main()
