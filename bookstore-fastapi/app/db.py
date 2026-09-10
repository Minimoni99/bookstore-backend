"""
Lightweight JSON-file "database". Fine for launch / low volume.
Every function here keeps the same shape so swapping in Postgres/SQLAlchemy
later is a contained change to this one file, not a rewrite of the routes.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
FILES = {
    "users": os.path.join(DATA_DIR, "users.json"),
    "books": os.path.join(DATA_DIR, "books.json"),
    "orders": os.path.join(DATA_DIR, "orders.json"),
    "subscriptions": os.path.join(DATA_DIR, "subscriptions.json"),
    "leads": os.path.join(DATA_DIR, "leads.json"),
}

os.makedirs(DATA_DIR, exist_ok=True)
for path in FILES.values():
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump([], f)


def read_all(table):
    with open(FILES[table], "r") as f:
        return json.load(f)


def write_all(table, rows):
    with open(FILES[table], "w") as f:
        json.dump(rows, f, indent=2)


def insert(table, row):
    rows = read_all(table)
    rows.append(row)
    write_all(table, rows)
    return row


def find(table, predicate):
    for row in read_all(table):
        if predicate(row):
            return row
    return None


def filter_rows(table, predicate):
    return [row for row in read_all(table) if predicate(row)]


def update(table, predicate, patch):
    rows = read_all(table)
    for i, row in enumerate(rows):
        if predicate(row):
            rows[i] = {**row, **patch}
            write_all(table, rows)
            return rows[i]
    return None


def remove(table, predicate):
    rows = read_all(table)
    next_rows = [r for r in rows if not predicate(r)]
    write_all(table, next_rows)
    return len(next_rows) != len(rows)
