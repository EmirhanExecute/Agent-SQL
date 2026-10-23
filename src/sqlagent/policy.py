"""Single source of truth for what the agent may see or call."""

# Columns hidden from schema/samples, rejected by the validator, and denied by the SQLite authorizer.
SENSITIVE_COLUMNS: dict[str, set[str]] = {
    "Customers": {"Phone", "Fax", "Address"},
    "Employees": {"HomePhone", "Address", "Notes"},
    "Suppliers": {"Phone", "Fax", "Address"},
    "Orders": {"ShipAddress"},
}
SENSITIVE_NAMES = {c.lower() for cols in SENSITIVE_COLUMNS.values() for c in cols}

DENIED_FUNCTIONS = {
    "load_extension", "readfile", "writefile", "edit", "fts3_tokenizer",
    "zeroblob", "randomblob", "sqlite_compileoption_get", "sqlite_compileoption_used",
}

QUERY_TIMEOUT_S = 5.0
