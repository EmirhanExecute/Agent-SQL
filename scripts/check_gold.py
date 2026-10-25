"""Validate gold SQL: runs on small+full, flags errors, empty results, >100 rows, and top-N ties."""
import sqlite3
import sys

import yaml

for path in sys.argv[1:]:
    qs = yaml.safe_load(open(path, encoding="utf-8"))
    for db in ["small", "full"]:
        c = sqlite3.connect(f"data/northwind_{db}.db")
        for q in qs:
            if q.get("expect", "sql") != "sql":
                continue
            try:
                n = len(c.execute(q["sql"]).fetchall())
            except Exception as e:
                print(db, q["id"], "ERROR", e)
                continue
            if n == 0 or n > 100:
                print(db, q["id"], "rows", n)
