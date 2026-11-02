import json

import pytest

from fcv import validator as v

WEATHER = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}, "days": {"type": "integer"}},
            "required": ["city"],
        },
    },
}


def make_line(calls, tools=None):
    return json.dumps({
        "id": "x",
        "tools": tools if tools is not None else [WEATHER],
        "messages": [{"role": "user", "content": "hi"}],
        "expected_tool_calls": [
            {"type": "function", "function": {"name": n, "arguments": a if isinstance(a, str) else json.dumps(a)}}
            for n, a in calls
        ],
    })


def types_of(line):
    return [i.error_type for i in v.validate_line(1, line).issues]


def test_valid_task_has_no_issues():
    res = v.validate_line(1, make_line([("get_weather", {"city": "Rio", "days": 2})]))
    assert res.ok
    assert res.called_tools == ["get_weather"]


@pytest.mark.parametrize("calls,expected", [
    ([("get_wether", {"city": "Rio"})], [v.UNKNOWN_TOOL]),
    ([("get_weather", {"days": 1})], [v.MISSING_REQUIRED_ARG]),
    ([("get_weather", {"city": 42})], [v.TYPE_MISMATCH]),
    ([("get_weather", {"city": "Rio", "lang": "pt"})], [v.EXTRA_ARG]),
    ([("get_weather", '{"city": "Rio"')], [v.MALFORMED_ARGUMENTS]),
    ([("get_weather", '["Rio"]')], [v.MALFORMED_ARGUMENTS]),
    ([("get_weather", {"city": "Rio"}), ("get_weather", {"city": "Rio"})], [v.DUPLICATE_CALL]),
])
def test_each_error_type(calls, expected):
    assert types_of(make_line(calls)) == expected


def test_duplicate_ignores_key_order():
    line = make_line([
        ("get_weather", '{"city": "Rio", "days": 1}'),
        ("get_weather", '{"days": 1, "city": "Rio"}'),
    ])
    assert types_of(line) == [v.DUPLICATE_CALL]


def test_same_tool_different_args_is_fine():
    line = make_line([("get_weather", {"city": "Rio"}), ("get_weather", {"city": "Recife"})])
    assert types_of(line) == []


def test_malformed_json_line():
    res = v.validate_line(3, '{"id": "a", ')
    assert [i.error_type for i in res.issues] == [v.MALFORMED_JSON]
    assert res.line_no == 3


def test_invalid_task_structure():
    assert types_of(make_line([], tools=[])) == [v.INVALID_TASK]


def test_bad_parameters_schema():
    bad = {"type": "function", "function": {"name": "f", "parameters": {"type": "nope"}}}
    assert v.INVALID_SCHEMA in types_of(make_line([], tools=[bad]))


def test_arguments_as_dict_are_accepted():
    line = json.dumps({
        "id": "d", "tools": [WEATHER], "messages": [{"role": "user", "content": "x"}],
        "expected_tool_calls": [{"function": {"name": "get_weather", "arguments": {"city": "Rio"}}}],
    })
    assert types_of(line) == []
