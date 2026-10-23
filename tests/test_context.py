import sys

import yaml

from sqlagent import context, db
from sqlagent.config import DB_PATH

sys.path.insert(0, "eval")


def test_categorical_values_include_discontinued_and_hide_restricted():
    vals = context.categorical_values(DB_PATH, "Products")
    assert vals["Discontinued"] == ["0", "1"]
    assert "Phone" not in context.categorical_values(DB_PATH, "Customers")
    assert "Country" in context.categorical_values(DB_PATH, "Customers")


def test_schema_with_values():
    schema = db.full_schema(DB_PATH, ["Products"], context.categorical_values)
    assert "values: '0', '1'" in schema


def test_link_values_exact_and_fuzzy():
    assert any("Products.ProductName" in h for h in context.link_values("How many units of Chai have been sold?"))
    assert any("Categories.CategoryName" in h for h in context.link_values("Seafod products please"))
    assert context.link_values("How many orders are there?") == []


def test_expand_tables_adds_junction():
    assert "Order Details" in context.expand_tables(["Orders", "Products"])


def test_fewshot_pool_has_no_test_questions():
    qs = yaml.safe_load(open("eval/questions.yaml", encoding="utf-8"))
    train = {q["q"].lower() for q in qs if q["split"] == "train"}
    test = {q["q"].lower() for q in qs if q["split"] == "test"}
    assert not train & test
    assert {q["id"] for q in qs if q["split"] == "train"}.isdisjoint({q["id"] for q in qs if q["split"] == "test"})


def test_result_comparison_is_order_and_column_insensitive():
    from run_eval import same_result
    assert same_result([("a", 1.004), ("b", 2)], [(2, "b"), (1.0, "A")])
    assert same_result([("x", 0.04996)], [("x", 0.05)])
    assert not same_result([("a", 1)], [("a", 2)])
    assert not same_result([("a", 1)], [("a", 1), ("b", 1)])
