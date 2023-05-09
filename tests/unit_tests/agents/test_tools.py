"""Test tool utils."""
from datetime import datetime
from functools import partial
from typing import Optional, Type, Union

import pydantic
import pytest
from pydantic import BaseModel

from langchain.agents.tools import Tool, tool
from langchain.tools.base import BaseTool, SchemaAnnotationError


def test_unnamed_decorator() -> None:
    """Test functionality with unnamed decorator."""

    @tool
    def search_api(query: str) -> str:
        """Search the API for the query."""
        return "API result"

    assert isinstance(search_api, Tool)
    assert search_api.name == "search_api"
    assert not search_api.return_direct
    assert search_api("test") == "API result"


class _MockSchema(BaseModel):
    arg1: int
    arg2: bool
    arg3: Optional[dict] = None


class _MockStructuredTool(BaseTool):
    name = "structured_api"
    args_schema: Type[BaseModel] = _MockSchema
    description = "A Structured Tool"

    def _run(self, arg1: int, arg2: bool, arg3: Optional[dict] = None) -> str:
        return f"{arg1} {arg2} {arg3}"

    async def _arun(self, arg1: int, arg2: bool, arg3: Optional[dict] = None) -> str:
        raise NotImplementedError


def test_structured_args() -> None:
    """Test functionality with structured arguments."""
    structured_api = _MockStructuredTool()
    assert isinstance(structured_api, BaseTool)
    assert structured_api.name == "structured_api"
    expected_result = "1 True {'foo': 'bar'}"
    args = {"arg1": 1, "arg2": True, "arg3": {"foo": "bar"}}
    assert structured_api.run(args) == expected_result


def test_unannotated_base_tool_raises_error() -> None:
    """Test that a BaseTool without type hints raises an exception.""" ""
    with pytest.raises(SchemaAnnotationError):

        class _UnAnnotatedTool(BaseTool):
            name = "structured_api"
            # This would silently be ignored without the custom metaclass
            args_schema = _MockSchema
            description = "A Structured Tool"

            def _run(self, arg1: int, arg2: bool, arg3: Optional[dict] = None) -> str:
                return f"{arg1} {arg2} {arg3}"

            async def _arun(
                self, arg1: int, arg2: bool, arg3: Optional[dict] = None
            ) -> str:
                raise NotImplementedError


def test_misannotated_base_tool_raises_error() -> None:
    """Test that a BaseTool with the incorrrect typehint raises an exception.""" ""
    with pytest.raises(SchemaAnnotationError):

        class _MisAnnotatedTool(BaseTool):
            name = "structured_api"
            # This would silently be ignored without the custom metaclass
            args_schema: BaseModel = _MockSchema  # type: ignore
            description = "A Structured Tool"

            def _run(self, arg1: int, arg2: bool, arg3: Optional[dict] = None) -> str:
                return f"{arg1} {arg2} {arg3}"

            async def _arun(
                self, arg1: int, arg2: bool, arg3: Optional[dict] = None
            ) -> str:
                raise NotImplementedError


def test_forward_ref_annotated_base_tool_accepted() -> None:
    """Test that a using forward ref annotation syntax is accepted.""" ""

    class _ForwardRefAnnotatedTool(BaseTool):
        name = "structured_api"
        args_schema: "Type[BaseModel]" = _MockSchema
        description = "A Structured Tool"

        def _run(self, arg1: int, arg2: bool, arg3: Optional[dict] = None) -> str:
            return f"{arg1} {arg2} {arg3}"

        async def _arun(
            self, arg1: int, arg2: bool, arg3: Optional[dict] = None
        ) -> str:
            raise NotImplementedError


def test_subclass_annotated_base_tool_accepted() -> None:
    """Test BaseTool child w/ custom schema isn't overwritten."""

    class _ForwardRefAnnotatedTool(BaseTool):
        name = "structured_api"
        args_schema: Type[_MockSchema] = _MockSchema
        description = "A Structured Tool"

        def _run(self, arg1: int, arg2: bool, arg3: Optional[dict] = None) -> str:
            return f"{arg1} {arg2} {arg3}"

        async def _arun(
            self, arg1: int, arg2: bool, arg3: Optional[dict] = None
        ) -> str:
            raise NotImplementedError

    assert issubclass(_ForwardRefAnnotatedTool, BaseTool)
    tool = _ForwardRefAnnotatedTool()
    assert tool.args_schema == _MockSchema


def test_decorator_with_specified_schema() -> None:
    """Test that manually specified schemata are passed through to the tool."""

    @tool(args_schema=_MockSchema)
    def tool_func(arg1: int, arg2: bool, arg3: Optional[dict] = None) -> str:
        """Return the arguments directly."""
        return f"{arg1} {arg2} {arg3}"

    assert isinstance(tool_func, Tool)
    assert tool_func.args_schema == _MockSchema


def test_decorated_function_schema_equivalent() -> None:
    """Test that a BaseTool without a schema meets expectations."""

    @tool
    def structured_tool_input(
        arg1: int, arg2: bool, arg3: Optional[dict] = None
    ) -> str:
        """Return the arguments directly."""
        return f"{arg1} {arg2} {arg3}"

    assert isinstance(structured_tool_input, Tool)
    assert (
        structured_tool_input.args_schema.schema()["properties"]
        == _MockSchema.schema()["properties"]
        == structured_tool_input.args
    )


def test_structured_args_decorator_no_infer_schema() -> None:
    """Test functionality with structured arguments parsed as a decorator."""

    @tool(infer_schema=False)
    def structured_tool_input(
        arg1: int, arg2: Union[float, datetime], opt_arg: Optional[dict] = None
    ) -> str:
        """Return the arguments directly."""
        return f"{arg1}, {arg2}, {opt_arg}"

    assert isinstance(structured_tool_input, Tool)
    assert structured_tool_input.name == "structured_tool_input"
    args = {"arg1": 1, "arg2": 0.001, "opt_arg": {"foo": "bar"}}
    expected_result = "1, 0.001, {'foo': 'bar'}"
    assert structured_tool_input.run(args) == expected_result


def test_structured_single_str_decorator_no_infer_schema() -> None:
    """Test functionality with structured arguments parsed as a decorator."""

    @tool(infer_schema=False)
    def unstructured_tool_input(tool_input: str) -> str:
        """Return the arguments directly."""
        return f"{tool_input}"

    assert isinstance(unstructured_tool_input, Tool)
    assert unstructured_tool_input.args_schema is None


def test_base_tool_inheritance_base_schema() -> None:
    """Test schema is correctly inferred when inheriting from BaseTool."""

    class _MockSimpleTool(BaseTool):
        name = "simple_tool"
        description = "A Simple Tool"

        def _run(self, tool_input: str) -> str:
            return f"{tool_input}"

        async def _arun(self, tool_input: str) -> str:
            raise NotImplementedError

    simple_tool = _MockSimpleTool()
    assert simple_tool.args_schema is None
    expected_args = {"tool_input": {"title": "Tool Input", "type": "string"}}
    assert simple_tool.args == expected_args


def test_tool_lambda_args_schema() -> None:
    """Test args schema inference when the tool argument is a lambda function."""

    tool = Tool(
        name="tool",
        description="A tool",
        func=lambda tool_input: tool_input,
    )
    assert tool.args_schema is None
    expected_args = {"tool_input": {"title": "Tool Input"}}
    assert tool.args == expected_args


def test_tool_lambda_multi_args_schema() -> None:
    """Test args schema inference when the tool argument is a lambda function."""
    tool = Tool(
        name="tool",
        description="A tool",
        func=lambda tool_input, other_arg: f"{tool_input}{other_arg}",  # type: ignore
    )
    assert tool.args_schema is None
    expected_args = {
        "tool_input": {"title": "Tool Input"},
        "other_arg": {"title": "Other Arg"},
    }
    assert tool.args == expected_args


def test_tool_partial_function_args_schema() -> None:
    """Test args schema inference when the tool argument is a partial function."""

    def func(tool_input: str, other_arg: str) -> str:
        return tool_input + other_arg

    with pytest.raises(pydantic.error_wrappers.ValidationError):
        # We don't yet support args_schema inference for partial functions
        # so want to make sure we proactively raise an error
        Tool(
            name="tool",
            description="A tool",
            func=partial(func, other_arg="foo"),
        )


def test_empty_args_decorator() -> None:
    """Test inferred schema of decorated fn with no args."""

    @tool
    def empty_tool_input() -> str:
        """Return a constant."""
        return "the empty result"

    assert isinstance(empty_tool_input, Tool)
    assert empty_tool_input.name == "empty_tool_input"
    assert empty_tool_input.args == {}
    assert empty_tool_input.run({}) == "the empty result"


def test_named_tool_decorator() -> None:
    """Test functionality when arguments are provided as input to decorator."""

    @tool("search")
    def search_api(query: str) -> str:
        """Search the API for the query."""
        return "API result"

    assert isinstance(search_api, Tool)
    assert search_api.name == "search"
    assert not search_api.return_direct


def test_named_tool_decorator_return_direct() -> None:
    """Test functionality when arguments and return direct are provided as input."""

    @tool("search", return_direct=True)
    def search_api(query: str) -> str:
        """Search the API for the query."""
        return "API result"

    assert isinstance(search_api, Tool)
    assert search_api.name == "search"
    assert search_api.return_direct


def test_unnamed_tool_decorator_return_direct() -> None:
    """Test functionality when only return direct is provided."""

    @tool(return_direct=True)
    def search_api(query: str) -> str:
        """Search the API for the query."""
        return "API result"

    assert isinstance(search_api, Tool)
    assert search_api.name == "search_api"
    assert search_api.return_direct


def test_tool_with_kwargs() -> None:
    """Test functionality when only return direct is provided."""

    @tool(return_direct=True)
    def search_api(
        arg_1: float,
        ping: str = "hi",
    ) -> str:
        """Search the API for the query."""
        return f"arg_1={arg_1}, ping={ping}"

    assert isinstance(search_api, Tool)
    result = search_api.run(
        tool_input={
            "arg_1": 3.2,
            "ping": "pong",
        }
    )
    assert result == "arg_1=3.2, ping=pong"

    result = search_api.run(
        tool_input={
            "arg_1": 3.2,
        }
    )
    assert result == "arg_1=3.2, ping=hi"


def test_missing_docstring() -> None:
    """Test error is raised when docstring is missing."""
    # expect to throw a value error if theres no docstring
    with pytest.raises(AssertionError):

        @tool
        def search_api(query: str) -> str:
            return "API result"


def test_create_tool_positional_args() -> None:
    """Test that positional arguments are allowed."""
    test_tool = Tool("test_name", lambda x: x, "test_description")
    assert test_tool("foo") == "foo"
    assert test_tool.name == "test_name"
    assert test_tool.description == "test_description"


def test_create_tool_keyword_args() -> None:
    """Test that keyword arguments are allowed."""
    test_tool = Tool(name="test_name", func=lambda x: x, description="test_description")
    assert test_tool("foo") == "foo"
    assert test_tool.name == "test_name"
    assert test_tool.description == "test_description"


@pytest.mark.asyncio
async def test_create_async_tool() -> None:
    """Test that async tools are allowed."""

    async def _test_func(x: str) -> str:
        return x

    test_tool = Tool(
        name="test_name",
        func=lambda x: x,
        description="test_description",
        coroutine=_test_func,
    )
    assert test_tool("foo") == "foo"
    assert test_tool.name == "test_name"
    assert test_tool.description == "test_description"
    assert test_tool.coroutine is not None
    assert await test_tool.arun("foo") == "foo"
