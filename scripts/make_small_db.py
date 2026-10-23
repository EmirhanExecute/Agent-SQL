"""Build northwind_small.db: a FK-consistent subset of northwind_full.db (first N orders)."""
import os
import sqlite3
import sys

N_ORDERS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
SRC, DST = "data/northwind_full.db", "data/northwind_small.db"

if os.path.exists(DST):
    os.remove(DST)
src = sqlite3.connect(SRC)
dst = sqlite3.connect(DST)
for (sql,) in src.execute("select sql from sqlite_master where sql is not null and name not like 'sqlite_%'"):
    dst.execute(sql)

def copy(table, where="", params=()):
    rows = src.execute(f"select * from [{table}] {where}", params).fetchall()
    if rows:
        dst.executemany(f"insert into [{table}] values ({','.join('?' * len(rows[0]))})", rows)

copy("Orders", "order by OrderID limit ?", (N_ORDERS,))
ids = [r[0] for r in dst.execute("select OrderID from Orders")]
q = ",".join("?" * len(ids))
copy("Order Details", f"where OrderID in ({q})", ids)
for table, col, parent in [
    ("Products", "ProductID", "select ProductID from [Order Details]"),
    ("Customers", "CustomerID", "select CustomerID from Orders"),
    ("Employees", "EmployeeID", "select EmployeeID from Orders"),
    ("Shippers", "ShipperID", "select ShipVia from Orders"),
]:
    keys = [r[0] for r in dst.execute(parent)]
    copy(table, f"where {col} in ({','.join('?' * len(keys))})", keys)
for table, col, parent in [
    ("Categories", "CategoryID", "select CategoryID from Products"),
    ("Suppliers", "SupplierID", "select SupplierID from Products"),
]:
    keys = [r[0] for r in dst.execute(parent)]
    copy(table, f"where {col} in ({','.join('?' * len(keys))})", keys)
copy("EmployeeTerritories", "where EmployeeID in (select EmployeeID from Employees)")
copy("Territories", "where TerritoryID in (select TerritoryID from EmployeeTerritories)")
copy("Regions", "where RegionID in (select RegionID from Territories)")
dst.commit()
for (t,) in dst.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'").fetchall():
    print(t, dst.execute(f"select count(*) from [{t}]").fetchone()[0])
