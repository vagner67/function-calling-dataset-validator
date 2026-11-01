import argparse
import sys

from . import db
from .report import report
from .validator import validate_file


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fcv", description="check function-calling datasets")
    parser.add_argument("--db", default="fcv.db")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("dataset")
    r = sub.add_parser("report")
    r.add_argument("--run", type=int, help="run id, default is the last one")
    args = parser.parse_args(argv)

    conn = db.connect(args.db)

    if args.cmd == "validate":
        try:
            results = list(validate_file(args.dataset))
        except FileNotFoundError:
            print("file not found:", args.dataset, file=sys.stderr)
            return 2
        run_id = db.save_run(conn, args.dataset, results)

        n_bad = 0
        for res in results:
            if res.ok:
                continue
            n_bad += 1
            where = f"line {res.line_no}" + (f" [{res.task_id}]" if res.task_id else "")
            for iss in res.issues:
                tool = f" {iss.tool_name}:" if iss.tool_name else ""
                print(f"{where} {iss.error_type}:{tool} {iss.message}")
        print(f"\n{len(results)} tasks, {len(results) - n_bad} ok, {n_bad} with errors. saved as run {run_id} in {args.db}")
        return 1 if n_bad else 0  # non zero so it fails in CI

    # report
    run_id = args.run or conn.execute("SELECT MAX(id) FROM runs").fetchone()[0]
    if run_id is None:
        print("no runs yet, run validate first", file=sys.stderr)
        return 2
    report(conn, run_id)
    return 0
