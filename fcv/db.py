import sqlite3
from datetime import datetime, timezone

TABLES = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    run_id INTEGER, line_no INTEGER, task_id TEXT, ok INTEGER
);
-- one row per expected call, need this for error rate per tool
CREATE TABLE IF NOT EXISTS calls (
    run_id INTEGER, line_no INTEGER, call_index INTEGER, tool_name TEXT
);
CREATE TABLE IF NOT EXISTS errors (
    run_id INTEGER, line_no INTEGER, task_id TEXT, tool_name TEXT,
    call_index INTEGER, error_type TEXT, message TEXT
);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.executescript(TABLES)
    return conn


def save_run(conn, dataset, results):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        run_id = conn.execute(
            "INSERT INTO runs (dataset, created_at) VALUES (?, ?)", (dataset, now)
        ).lastrowid
        for r in results:
            conn.execute("INSERT INTO tasks VALUES (?,?,?,?)", (run_id, r.line_no, r.task_id, int(r.ok)))
            for i, name in enumerate(r.called_tools):
                conn.execute("INSERT INTO calls VALUES (?,?,?,?)", (run_id, r.line_no, i, name))
            for iss in r.issues:
                conn.execute(
                    "INSERT INTO errors VALUES (?,?,?,?,?,?,?)",
                    (run_id, r.line_no, r.task_id, iss.tool_name, iss.call_index, iss.error_type, iss.message),
                )
    return run_id
