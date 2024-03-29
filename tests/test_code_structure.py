"""Test codestructure."""

import ast
import contextlib
import textwrap
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

from codestructure import (
    Class,
    ExtractedInfo,
    Function,
    Parameter,
    add_parent_list,
    main,
    parse_module,
)

REPO_ROOT = Path(__file__).parent.parent


def test_parse_module() -> None:
    """Test parse_module."""
    source_code = textwrap.dedent(
        """
        def example_function():
            pass
        """,
    )
    ast_module = parse_module(source_code=source_code)
    assert isinstance(ast_module, ast.Module)


def test_add_parent_list() -> None:
    """Test add_parent_list."""
    source_code = textwrap.dedent(
        """
        class ExampleClass:
            def example_method(self):
                pass
        """,
    )
    ast_module = parse_module(source_code=source_code)
    example_class_node = None
    example_method_node = None

    for node in ast.walk(ast_module):
        if isinstance(node, ast.ClassDef):
            example_class_node = node
        elif isinstance(node, ast.FunctionDef):
            example_method_node = node

    assert example_method_node.parent_list[-1] == example_class_node  # type: ignore[union-attr]


def test_extract_function_info() -> None:
    """Test ExtractedInfo.from_ast."""
    source_code = textwrap.dedent(
        """

        def example_function(a: int, b: int = 2) -> int:
            \"\"\"An example function.\"\"\"
            return a + b

        class ExampleClass:
            x: int
            y: int = 3

            def example_method(self) -> None:
                \"\"\"An example method.\"\"\"
                pass
        """,
    )

    ast_module = ast.parse(source_code)
    add_parent_list(ast_module)
    extracted_functions = ExtractedInfo.from_ast(ast_module)

    expected_functions = ExtractedInfo(
        classes=[
            Class(
                class_name="ExampleClass",
                attributes=[("x", "int"), ("y", "int")],
                functions=[
                    Function(
                        name="example_method",
                        docstring="An example method.",
                        decorator=None,
                        parameters=[Parameter("self", None, None)],
                        return_type="None",
                    ),
                ],
            ),
        ],
        functions=[
            (
                Function(
                    name="example_function",
                    docstring="An example function.",
                    decorator=None,
                    parameters=[
                        Parameter("a", "int", None),
                        Parameter("b", "int", 2),
                    ],
                    return_type="int",
                )
            ),
        ],
    )

    assert extracted_functions == expected_functions


def test_print_function_info_with_private() -> None:
    """Test ExtractedInfo.print with private functions included."""
    extracted_functions = ExtractedInfo(
        classes=[
            Class(
                class_name="ExampleClass",
                attributes=[("x", "int"), ("y", "int")],
                functions=[
                    Function(
                        name="_example_private_method",
                        docstring="An example private method.",
                        decorator=None,
                        parameters=[Parameter("self", None, None)],
                        return_type="None",
                    ),
                ],
            ),
        ],
        functions=[
            (
                Function(
                    name="_example_private_function",
                    docstring="An example private function.",
                    decorator=None,
                    parameters=[
                        Parameter("a", "int", None),
                        Parameter("b", "int", 2),
                    ],
                    return_type="int",
                )
            ),
        ],
    )

    expected_output = textwrap.dedent(
        """\
        class ExampleClass:
            x: int
            y: int
            def _example_private_method(self) -> None:
                \"\"\"An example private method.\"\"\"


        def _example_private_function(a: int, b: int = 2) -> int:
            \"\"\"An example private function.\"\"\"
        """,
    )

    with StringIO() as string, contextlib.redirect_stdout(string):
        ExtractedInfo.print(extracted_functions, with_private=True)
        output = string.getvalue()

    assert output.strip() == expected_output.strip()


def test_print_function_info_without_private() -> None:
    """Test ExtractedInfo.print without private functions."""
    extracted_functions = ExtractedInfo(
        classes=[
            Class(
                class_name="ExampleClass",
                attributes=[("x", "int"), ("y", "int")],
                functions=[
                    Function(
                        name="_example_private_method",
                        docstring="An example private method.",
                        decorator=None,
                        parameters=[Parameter("self", None, None)],
                        return_type="None",
                    ),
                ],
            ),
        ],
        functions=[
            (
                Function(
                    name="_example_private_function",
                    docstring="An example private function.",
                    decorator=None,
                    parameters=[
                        Parameter("a", "int", None),
                        Parameter("b", "int", 2),
                    ],
                    return_type="int",
                )
            ),
        ],
    )

    expected_output = textwrap.dedent(
        """\
        class ExampleClass:
            x: int
            y: int
        """,
    )

    with StringIO() as string, contextlib.redirect_stdout(string):
        ExtractedInfo.print(extracted_functions, with_private=False)
        output = string.getvalue()

    assert output.strip() == expected_output.strip()


def test_main() -> None:
    """Test main function."""
    module_file_path = "test_module.py"
    source_code = textwrap.dedent(
        """
        def example_function(a: int, b: int = 2) -> int:
            \"\"\"An example function.\"\"\"
            return a + b

        class ExampleClass:
            x: int
            y: int = 3

            def example_method(self) -> None:
                \"\"\"An example method.\"\"\"
                pass
        """,
    )
    with open(module_file_path, "w") as f:  # noqa: PTH123
        f.write(source_code)

    expected_output = textwrap.dedent(
        """
        class ExampleClass:
            x: int
            y: int
            def example_method(self) -> None:
                \"\"\"An example method.\"\"\"


        def example_function(a: int, b: int = 2) -> int:
            \"\"\"An example function.\"\"\"
        """,
    )

    args = ["codestructure", module_file_path, "--no-private", "--no-rich", "--no-copy"]
    with (
        mock.patch("sys.argv", args),
        StringIO() as string,
        contextlib.redirect_stdout(
            string,
        ),
    ):
        main()
        output = string.getvalue()

    assert output.strip() == expected_output.strip()


def test_extract_function_info_with_decorator() -> None:
    """Test ExtractedInfo.from_ast with a decorated function."""
    source_code = textwrap.dedent(
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

        @decorator
        def example_function(a: int, b: int = 2) -> int:
            \"\"\"An example function.\"\"\"
            return a + b
        """,
    )

    ast_module = ast.parse(source_code)
    add_parent_list(ast_module)
    extracted_functions = ExtractedInfo.from_ast(ast_module)

    expected_functions = ExtractedInfo(
        functions=[
            Function(
                name="decorator",
                docstring=None,
                decorator=None,
                parameters=[
                    Parameter("func", None, None),
                ],
                return_type=None,
            ),
            Function(
                name="example_function",
                docstring="An example function.",
                decorator="decorator",
                parameters=[
                    Parameter("a", "int", None),
                    Parameter("b", "int", 2),
                ],
                return_type="int",
            ),
        ],
    )

    assert extracted_functions == expected_functions


def test_extract_function_info_with_value_error_in_literal_eval() -> None:
    """Test ExtractedInfo.from_ast with a ValueError in ast.literal_eval."""
    source_code = textwrap.dedent(
        """
        custom_default_value = 1
        CONST = 2
        def example_function(a: int = custom_default_value, *, b: int = CONST):
            pass
        """,
    )
    expected_functions = ExtractedInfo(
        functions=[
            (
                Function(
                    name="example_function",
                    docstring=None,
                    decorator=None,
                    parameters=[
                        Parameter("a", "int", "custom_default_value"),
                        Parameter("b", "int", "CONST", kw_only=True),
                    ],
                    return_type=None,
                )
            ),
        ],
    )

    tree = parse_module(source_code=source_code)
    function_info = ExtractedInfo.from_ast(tree)

    assert function_info == expected_functions


def test_print_function_info_with_class_docstring() -> None:
    """Test ExtractedInfo.print with a class that has a docstring."""
    extracted_functions = ExtractedInfo(
        classes=[
            Class(
                class_name="Foo",
                docstring="Some exception.",
                attributes=[],
                functions=[],
            ),
        ],
        functions=[],
    )

    expected_output = textwrap.dedent(
        """\
        class Foo:
            \"\"\"Some exception.\"\"\"
        """,
    )

    with StringIO() as string, contextlib.redirect_stdout(string):
        ExtractedInfo.print(extracted_functions, with_private=True)
        output = string.getvalue()

    assert output.strip() == expected_output.strip()


def test_print_function_info_with_class_attribute() -> None:
    """Test ExtractedInfo.print with a class that has an attribute."""
    extracted_functions = ExtractedInfo(
        classes=[
            Class(
                class_name="A",
                docstring=None,
                attributes=[("x", "int")],
                functions=[],
                decorator="dataclass",
            ),
        ],
        functions=[],
    )

    expected_output = textwrap.dedent(
        """
        @dataclass
        class A:
            x: int
        """,
    )

    with StringIO() as string, contextlib.redirect_stdout(string):
        ExtractedInfo.print(extracted_functions, with_private=True)
        output = string.getvalue()

    assert output.strip() == expected_output.strip()


def test_print_function_info_with_private_class_attribute() -> None:
    """Test ExtractedInfo.print with a class that has a private attribute."""
    extracted_functions = ExtractedInfo(
        classes=[
            Class(
                class_name="A",
                docstring=None,
                attributes=[("_priv", "bool")],
                functions=[],
            ),
        ],
        functions=[],
    )

    expected_output = textwrap.dedent(
        """\
        class A:
            ...
        """,
    )

    with StringIO() as string, contextlib.redirect_stdout(string):
        ExtractedInfo.print(extracted_functions, with_private=False)
        output = string.getvalue()

    assert output.strip() == expected_output.strip()


def test_example_file() -> None:
    """Test example file."""
    test_file = REPO_ROOT / "tests" / "example.py"
    with test_file.open() as f:
        source_code = f.read()

    tree = parse_module(source_code=source_code)
    function_info = ExtractedInfo.from_ast(tree)

    with StringIO() as string, contextlib.redirect_stdout(string):
        ExtractedInfo.print(function_info, with_private=False)
        output = string.getvalue()
    expected = textwrap.dedent(
        """
        class MyClass:
            my_attr: str
            def my_method(self, arg1: int) -> bool:
                \"\"\"My docstring.\"\"\"


        def my_function(arg2: float) -> None:
            ...
        """,
    )
    assert output.strip() == expected.strip()


def test_keyword_only_function() -> None:
    """Test a function with a keyword-only argument."""
    extracted_functions = ExtractedInfo(
        classes=[],
        functions=[
            (
                Function(
                    name="f",
                    docstring=None,
                    decorator=None,
                    parameters=[
                        Parameter(name="x", param_type=None, default_value=None),
                        Parameter(
                            name="y",
                            param_type="int",
                            default_value=1,
                            kw_only=True,
                        ),
                    ],
                    return_type=None,
                )
            ),
        ],
    )

    expected_output = textwrap.dedent(
        """\
        def f(x, *, y: int = 1) -> None:
            ...
        """,
    )

    with StringIO() as string, contextlib.redirect_stdout(string):
        ExtractedInfo.print(extracted_functions, with_private=False)
        output = string.getvalue()

    assert output.strip() == expected_output.strip()


def test_get_class_name() -> None:
    """Test Class.get_class_name."""
    source_code = textwrap.dedent(
        """
        class A:
            def method1(self):
                pass
        """,
    )
    tree = parse_module(source_code=source_code)
    ast.increment_lineno(tree, 1)
    function_node = tree.body[0].body[0]  # type: ignore[attr-defined]
    assert Class.get_class_name(function_node, ["A"]) == "A"


def test_get_decorator_name() -> None:
    """Test Class.get_decorator_name."""
    source_code = textwrap.dedent(
        """
        @my_decorator
        def my_function():
            pass
        """,
    )
    tree = parse_module(source_code=source_code)
    ast.increment_lineno(tree, 1)
    function_node = tree.body[0]
    assert Class.get_decorator_name(function_node) == "my_decorator"  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("source_code", "expected"),
    [
        (
            textwrap.dedent(
                """
                def my_function(x: int, y: float, *, z: str = 'abc'):
                    pass
                """,
            ),
            [
                Parameter("x", "int", None, False),  # noqa: FBT003
                Parameter("y", "float", None, False),  # noqa: FBT003
                Parameter("z", "str", "abc", True),  # noqa: FBT003
            ],
        ),
        (
            textwrap.dedent(
                """
                def my_function(a: int = 1, b: float = 2.0, c: str = 'test'):
                    pass
                """,
            ),
            [
                Parameter("a", "int", 1, False),  # noqa: FBT003
                Parameter("b", "float", 2.0, False),  # noqa: FBT003
                Parameter("c", "str", "test", False),  # noqa: FBT003
            ],
        ),
        (
            textwrap.dedent(
                """
                def my_function(a: int, b: float, *args, **kwargs):
                    pass
                """,
            ),
            [
                Parameter("a", "int", None, False),  # noqa: FBT003
                Parameter("b", "float", None, False),  # noqa: FBT003
            ],
        ),
    ],
)
def test_get_parameters(source_code: str, expected: list[Parameter]) -> None:
    """Test Function.get_parameters."""
    tree = parse_module(source_code=source_code)
    ast.increment_lineno(tree, 1)
    function_node = tree.body[0]
    parameters = Function.get_parameters(function_node)  # type: ignore[arg-type]
    assert parameters == expected
