# function-calling-dataset-validator

Small script to check function-calling datasets (OpenAI `tools` format) before using them for training or evals.

I made this because my own tool-use tasks had a lot of dumb mistakes. Typos in tool names, numbers as strings, args that are not in the schema, a JSON line missing a brace. It is easy to miss them by hand when the file has hundreds of lines.

## What it does

It reads a JSONL file, one task per line. Each task has `tools`, `messages` and `expected_tool_calls`. For every expected call it checks that the tool exists, required args are there, types match the JSON Schema, there are no extra args and no duplicate calls. It also catches lines that are not valid JSON.

Each run is saved in a SQLite file (`fcv.db`), so the `report` command can show the error rate per tool and per error type.

Look at `examples/sample_tasks.jsonl` to see the format.

## Running it

Needs Python 3.10+.

```
pip install -r requirements.txt
python -m fcv validate examples/sample_tasks.jsonl
python -m fcv report
```

`--db somefile.db` goes before the command if you want another db. `report --run 2` shows an older run. `validate` exits with 1 when it finds errors.

Tests: `python -m pytest`

## Example

The sample file has 15 tasks and most are broken on purpose. Output from a real run:

```
$ python -m fcv validate examples/sample_tasks.jsonl
line 5 [t05] unknown_tool: get_wheather: tool 'get_wheather' is not in the tools list
line 6 [t06] missing_required_arg: search_flights: missing required arg 'origin'
line 7 [t07] type_mismatch: search_flights: passengers: '3' is not of type 'integer'
line 8 [t08] type_mismatch: convert_currency: amount: '50' is not of type 'number'
line 9 [t09] extra_arg: send_email: arg 'cc' is not in the tool schema
line 10 [t10] duplicate_call: get_weather: same call as index 0
line 11 [t11] malformed_arguments: convert_currency: arguments is not a valid JSON object
line 12 [t12] schema_violation: get_weather: unit: 'kelvin' is not one of ['celsius', 'fahrenheit']
line 13 [t13] schema_violation: search_flights: passengers: 0 is less than the minimum of 1
line 13 [t13] extra_arg: get_weather: arg 'units' is not in the tool schema
line 14 [t14] invalid_task: tools: List should have at least 1 item after validation, not 0
line 15 malformed_json: line is not valid JSON: Expecting ',' delimiter

15 tasks, 4 ok, 11 with errors. saved as run 1 in fcv.db

$ python -m fcv report
Run #1  examples/sample_tasks.jsonl  (2026-11-02T15:13:53+00:00)
Tasks: 15  ok: 4  with errors: 11  error rate: 73.3%

Error rate per tool (calls with at least one error)
tool              calls  bad  rate_%
----------------  -----  ---  ------
get_wheather      1      1    100.0
search_flights    4      3    75.0
convert_currency  3      2    66.7
get_weather       6      3    50.0
send_email        2      1    50.0

Errors per type
error_type            count  tasks  %_tasks
--------------------  -----  -----  -------
extra_arg             2      2      13.3
schema_violation      2      2      13.3
type_mismatch         2      2      13.3
duplicate_call        1      1      6.7
invalid_task          1      1      6.7
malformed_arguments   1      1      6.7
malformed_json        1      1      6.7
missing_required_arg  1      1      6.7
unknown_tool          1      1      6.7
```

## Notes

- It only checks the expected calls against the schema. It does not check if the call makes sense for the user message.
- Extra args are flagged even if the schema has no `additionalProperties: false`. Maybe I make this optional later.

MIT license.
