import pytest

from sqlagent import db
from sqlagent.security import validate_sql

TABLES = db.list_tables()


def ok(sql):
    return validate_sql(sql, TABLES)


@pytest.mark.parametrize("sql", [
    "DROP TABLE Orders",
    "DELETE FROM Orders",
    "UPDATE Products SET UnitPrice = 0",
    "INSERT INTO Shippers (CompanyName) VALUES ('x')",
    "CREATE TABLE t (a int)",
    "ALTER TABLE Orders ADD COLUMN x int",
    "PRAGMA table_info(Orders)",
    "ATTACH DATABASE 'x.db' AS x",
    "SELECT 1; DROP TABLE Orders",
    "SELECT * FROM Orders; SELECT * FROM Products",
    "SELECT load_extension('x')",
    "SELECT readfile('/etc/passwd')",
    "SELECT * FROM sqlite_master",
    "SELECT * FROM pragma_table_info('Orders')",
    "SELECT name FROM Nope",
    "SELECT Phone FROM Customers",
    "SELECT c.phone FROM Customers c",
    "SELECT * FROM Employees",
    "WITH x AS (SELECT * FROM Customers) SELECT * FROM x",
    "SELECT zeroblob(1000000000)",
    "not sql at all (",
])
def test_rejected(sql):
    assert not ok(sql).ok


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM Customers",
    "SELECT CompanyName, City FROM Customers",
    "SELECT * FROM Products",
    "WITH t AS (SELECT CustomerID, COUNT(*) n FROM Orders GROUP BY 1) SELECT * FROM t ORDER BY n DESC",
    'SELECT p.ProductName FROM Products p JOIN "Order Details" od ON od.ProductID = p.ProductID',
    "SELECT City FROM Customers UNION SELECT City FROM Suppliers",
])
def test_accepted(sql):
    assert ok(sql).ok


def test_limit_added_and_capped():
    assert ok("SELECT ProductName FROM Products").sql.endswith("LIMIT 100")
    assert ok("SELECT ProductName FROM Products LIMIT 5").sql.endswith("LIMIT 5")
    assert ok("SELECT ProductName FROM Products LIMIT 100000").sql.endswith("LIMIT 100")
    assert "LIMIT 100" in ok("SELECT City FROM Customers UNION SELECT City FROM Suppliers").sql


def test_engine_blocks_even_if_validator_bypassed():
    import sqlite3
    for sql in ["SELECT Phone FROM Customers", "SELECT * FROM sqlite_master", "DELETE FROM Orders",
                "SELECT load_extension('x')"]:
        with pytest.raises(sqlite3.Error):
            db.run_query(sql)


def test_timeout():
    import sqlite3
    from sqlagent import db as d
    from sqlagent.config import DB_PATH
    c = d.connect_hardened(DB_PATH, timeout_s=0.2)
    with pytest.raises(sqlite3.OperationalError):
        c.execute("WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM r) SELECT count(*) FROM r").fetchall()


def test_schema_hides_sensitive_columns():
    assert "Phone" not in db.get_schema("Customers")
    assert "HomePhone" not in db.get_schema("Employees")
    assert "CompanyName" in db.get_schema("Customers")
