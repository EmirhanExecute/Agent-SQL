from sqlagent.viz import choose_chart


def test_bar_for_category_plus_number():
    s = choose_chart(["CategoryName", "n"], [("Beverages", 12), ("Seafood", 12)])
    assert (s.kind, s.x, s.ys) == ("bar", "CategoryName", ("n",))


def test_line_for_time_series():
    s = choose_chart(["m", "revenue"], [("1996-07", 10.5), ("1996-08", 20.0)])
    assert s.kind == "line"


def test_multiple_numeric_columns_capped_at_three():
    s = choose_chart(["k", "a", "b", "c", "d"], [("x", 1, 2, 3, 4), ("y", 1, 2, 3, 4)])
    assert s.ys == ("a", "b", "c")


def test_id_first_column_is_treated_as_category():
    assert choose_chart(["OrderID", "total"], [(1, 5.0), (2, 6.0)]).kind == "bar"


def test_no_chart_cases():
    assert choose_chart(["n"], [(5,)]).kind == "none"
    assert choose_chart(["a", "b"], [("x", "y"), ("z", "w")]).kind == "none"
    assert choose_chart(["a", "b"], [(1, 2), (3, 4)]).kind == "none"
    many = [(f"c{i}", i) for i in range(40)]
    assert choose_chart(["k", "v"], many).kind == "none"
