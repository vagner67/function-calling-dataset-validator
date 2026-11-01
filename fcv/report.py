# the sql here is plain on purpose, you can paste it in `sqlite3 fcv.db` and play with it

PER_TOOL_SQL = """
SELECT c.tool_name,
       COUNT(*) AS calls,
       SUM(e.n IS NOT NULL) AS bad,
       ROUND(100.0 * SUM(e.n IS NOT NULL) / COUNT(*), 1) AS rate
FROM calls c
LEFT JOIN (
    SELECT line_no, call_index, COUNT(*) AS n FROM errors
    WHERE run_id = :run AND call_index IS NOT NULL
    GROUP BY line_no, call_index
) e ON e.line_no = c.line_no AND e.call_index = c.call_index
WHERE c.run_id = :run
GROUP BY c.tool_name
ORDER BY rate DESC, c.tool_name
"""

PER_TYPE_SQL = """
SELECT error_type, COUNT(*), COUNT(DISTINCT line_no),
       ROUND(100.0 * COUNT(DISTINCT line_no) / (SELECT COUNT(*) FROM tasks WHERE run_id = :run), 1)
FROM errors WHERE run_id = :run
GROUP BY error_type
ORDER BY COUNT(*) DESC, error_type
"""


def print_table(headers, rows):
    rows = [[str(x) for x in r] for r in rows]
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip())
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip())


def report(conn, run_id):
    dataset, created = conn.execute("SELECT dataset, created_at FROM runs WHERE id=?", (run_id,)).fetchone()
    total, ok = conn.execute("SELECT COUNT(*), SUM(ok) FROM tasks WHERE run_id=?", (run_id,)).fetchone()
    rate = round(100 * (total - ok) / total, 1) if total else 0

    print(f"Run #{run_id}  {dataset}  ({created})")
    print(f"Tasks: {total}  ok: {ok}  with errors: {total - ok}  error rate: {rate}%")
    print()
    print("Error rate per tool (calls with at least one error)")
    print_table(["tool", "calls", "bad", "rate_%"], conn.execute(PER_TOOL_SQL, {"run": run_id}))
    print()
    print("Errors per type")
    print_table(["error_type", "count", "tasks", "%_tasks"], conn.execute(PER_TYPE_SQL, {"run": run_id}))
    # TODO: compare two runs? would be nice to see if a dataset got better
