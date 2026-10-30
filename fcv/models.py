from typing import Any, Literal

from pydantic import BaseModel, Field


class FunctionDef(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    parameters: dict[str, Any] = {"type": "object", "properties": {}}


class Tool(BaseModel):
    type: Literal["function"] = "function"
    function: FunctionDef


class Message(BaseModel):
    role: str
    content: str | None = None  # assistant msgs can have no content


class FunctionCall(BaseModel):
    name: str
    # openai sends this as a json string. some datasets i found use a dict, so accept both
    arguments: str | dict[str, Any]


class ToolCall(BaseModel):
    id: str | None = None
    type: Literal["function"] = "function"
    function: FunctionCall


class Task(BaseModel):
    id: str
    tools: list[Tool] = Field(min_length=1)
    messages: list[Message] = Field(min_length=1)
    expected_tool_calls: list[ToolCall]
    # TODO: check that messages has at least one user msg?
