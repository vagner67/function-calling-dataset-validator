import json
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pydantic import ValidationError

from .models import Task

MALFORMED_JSON = "malformed_json"
INVALID_TASK = "invalid_task"
INVALID_SCHEMA = "invalid_schema"
MALFORMED_ARGUMENTS = "malformed_arguments"
UNKNOWN_TOOL = "unknown_tool"
MISSING_REQUIRED_ARG = "missing_required_arg"
TYPE_MISMATCH = "type_mismatch"
EXTRA_ARG = "extra_arg"
SCHEMA_VIOLATION = "schema_violation"
DUPLICATE_CALL = "duplicate_call"


@dataclass
class Issue:
    error_type: str
    message: str
    tool_name: str = None
    call_index: int = None


@dataclass
class TaskResult:
    line_no: int
    task_id: str
    issues: list = field(default_factory=list)
    called_tools: list = field(default_factory=list)

    @property
    def ok(self):
        return len(self.issues) == 0


def parse_args(raw):
    if isinstance(raw, dict):
        return raw
    try:
        val = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(val, dict):
        return None  # e.g. '["Rio"]' is valid json but not args
    return val


def check_arguments(name, args, schema, idx):
    issues = []
    props = schema.get("properties") or {}

    for req in schema.get("required", []):
        if req not in args:
            issues.append(Issue(MISSING_REQUIRED_ARG, f"missing required arg '{req}'", name, idx))

    # flag extra args even if schema doesnt say additionalProperties: false.
    # model should only send what the tool declares
    for k in args:
        if k not in props:
            issues.append(Issue(EXTRA_ARG, f"arg '{k}' is not in the tool schema", name, idx))

    for err in Draft202012Validator(schema).iter_errors(args):
        if err.validator in ("required", "additionalProperties"):
            continue  # already done above, dont want it twice
        path = ".".join(str(p) for p in err.absolute_path) or "(root)"
        etype = TYPE_MISMATCH if err.validator == "type" else SCHEMA_VIOLATION
        issues.append(Issue(etype, f"{path}: {err.message}", name, idx))
    # TODO: nested objects only get checked by jsonschema, extra_arg is top level only
    return issues


def validate_task(task):
    issues = []
    schemas = {}
    for t in task.tools:
        try:
            Draft202012Validator.check_schema(t.function.parameters)
        except SchemaError as e:
            issues.append(Issue(INVALID_SCHEMA, f"bad parameters schema: {e.message}", t.function.name))
            continue
        schemas[t.function.name] = t.function.parameters
    tool_names = [t.function.name for t in task.tools]

    seen = {}
    called = []
    for i, call in enumerate(task.expected_tool_calls):
        name = call.function.name
        called.append(name)
        if name not in tool_names:
            issues.append(Issue(UNKNOWN_TOOL, f"tool '{name}' is not in the tools list", name, i))
            continue

        args = parse_args(call.function.arguments)
        if args is None:
            issues.append(Issue(MALFORMED_ARGUMENTS, "arguments is not a valid JSON object", name, i))
            continue

        # sort_keys so {"a":1,"b":2} and {"b":2,"a":1} count as the same call
        key = name + json.dumps(args, sort_keys=True)
        if key in seen:
            issues.append(Issue(DUPLICATE_CALL, f"same call as index {seen[key]}", name, i))
        else:
            seen[key] = i

        if name in schemas:  # if schema was broken we already reported it
            issues += check_arguments(name, args, schemas[name], i)
    return issues, called


def validate_line(line_no, line):
    try:
        data = json.loads(line)
    except json.JSONDecodeError as e:
        return TaskResult(line_no, None, [Issue(MALFORMED_JSON, f"line is not valid JSON: {e.msg}")])

    task_id = data.get("id") if isinstance(data, dict) else None
    try:
        task = Task.model_validate(data)
    except ValidationError as e:
        errs = e.errors()
        loc = ".".join(str(x) for x in errs[0]["loc"])
        msg = f"{loc}: {errs[0]['msg']}"
        if len(errs) > 1:
            msg += f" (+{len(errs) - 1} more)"
        return TaskResult(line_no, task_id, [Issue(INVALID_TASK, msg)])

    issues, called = validate_task(task)
    return TaskResult(line_no, task.id, issues, called)


def validate_file(path):
    # TODO: this reads everything into a list in cli.py, fine for now
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, start=1):
            if line.strip():
                yield validate_line(n, line)
