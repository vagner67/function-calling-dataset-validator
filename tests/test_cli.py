import sqlite3
from pathlib import Path

from fcv.cli import main

SAMPLE = Path(__file__).parent.parent / "examples" / "sample_tasks.jsonl"


def test_sample_file(tmp_path, capsys):
    dbfile = tmp_path / "t.db"
    assert main(["--db", str(dbfile), "validate", str(SAMPLE)]) == 1  # sample is broken on purpose

    conn = sqlite3.connect(dbfile)
    assert conn.execute("SELECT COUNT(*), SUM(ok) FROM tasks").fetchone() == (15, 4)
    types = {r[0] for r in conn.execute("SELECT DISTINCT error_type FROM errors")}
    for t in ["unknown_tool", "missing_required_arg", "type_mismatch", "extra_arg",
              "duplicate_call", "malformed_json", "malformed_arguments"]:
        assert t in types

    capsys.readouterr()
    assert main(["--db", str(dbfile), "report"]) == 0
    out = capsys.readouterr().out
    assert "error rate: 73.3%" in out
    assert "search_flights" in out


def test_good_file(tmp_path):
    f = tmp_path / "ok.jsonl"
    f.write_text(SAMPLE.read_text().splitlines()[0] + "\n")
    assert main(["--db", str(tmp_path / "a.db"), "validate", str(f)]) == 0


def test_report_empty_db(tmp_path):
    assert main(["--db", str(tmp_path / "empty.db"), "report"]) == 2


def test_missing_file(tmp_path):
    assert main(["--db", str(tmp_path / "a.db"), "validate", "nope.jsonl"]) == 2
