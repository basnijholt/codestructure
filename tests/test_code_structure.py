"""Test codestructure."""
import ast
import contextlib
import textwrap
from io import StringIO

from codestructure import (
    Class,
    ExtractedFunctions,
    Function,
    Parameter,
    add_parent_list,
    extract_function_info,
    print_function_info,
)


def test_parse_module_file() -> None:
    """Test parse_module_file."""
    source_code = textwrap.dedent(
        """
        def example_function():
            pass
        """,
    )
    ast_module = ast.parse(source_code)
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
    ast_module = ast.parse(source_code)
    add_parent_list(ast_module)
    example_class_node = None
    example_method_node = None

    for node in ast.walk(ast_module):
        if isinstance(node, ast.ClassDef):
            example_class_node = node
        elif isinstance(node, ast.FunctionDef):
            example_method_node = node

    assert example_method_node.parent_list[-1] == example_class_node  # type: ignore[union-attr]


def test_extract_function_info() -> None:
    """Test extract_function_info."""
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
    extracted_functions = extract_function_info(ast_module)

    expected_functions = ExtractedFunctions(
        classes={
            "ExampleClass": Class(
                class_name="ExampleClass",
                attributes=[("x", "int"), ("y", "int")],
                functions={
                    "example_method": Function(
                        signature="example_method",
                        docstring="An example method.",
                        decorator=None,
                        parameters=[Parameter("self", None, None)],
                        return_type="None",
                    ),
                },
            ),
        },
        functions={
            "example_function": Function(
                signature="example_function",
                docstring="An example function.",
                decorator=None,
                parameters=[
                    Parameter("a", "int", None),
                    Parameter("b", "int", 2),
                ],
                return_type="int",
            ),
        },
    )

    assert extracted_functions == expected_functions


def test_print_function_info_with_private() -> None:
    """Test print_function_info with private functions included."""
    extracted_functions = ExtractedFunctions(
        classes={
            "ExampleClass": Class(
                class_name="ExampleClass",
                attributes=[("x", "int"), ("y", "int")],
                functions={
                    "_example_private_method": Function(
                        signature="_example_private_method",
                        docstring="An example private method.",
                        decorator=None,
                        parameters=[Parameter("self", None, None)],
                        return_type="None",
                    ),
                },
            ),
        },
        functions={
            "_example_private_function": Function(
                signature="_example_private_function",
                docstring="An example private function.",
                decorator=None,
                parameters=[
                    Parameter("a", "int", None),
                    Parameter("b", "int", 2),
                ],
                return_type="int",
            ),
        },
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
        print_function_info(extracted_functions, with_private=True)
        output = string.getvalue()

    assert output.strip() == expected_output.strip()


def test_print_function_info_without_private() -> None:
    """Test print_function_info without private functions."""
    extracted_functions = ExtractedFunctions(
        classes={
            "ExampleClass": Class(
                class_name="ExampleClass",
                attributes=[("x", "int"), ("y", "int")],
                functions={
                    "_example_private_method": Function(
                        signature="_example_private_method",
                        docstring="An example private method.",
                        decorator=None,
                        parameters=[Parameter("self", None, None)],
                        return_type="None",
                    ),
                },
            ),
        },
        functions={
            "_example_private_function": Function(
                signature="_example_private_function",
                docstring="An example private function.",
                decorator=None,
                parameters=[
                    Parameter("a", "int", None),
                    Parameter("b", "int", 2),
                ],
                return_type="int",
            ),
        },
    )

    expected_output = textwrap.dedent(
        """\
        class ExampleClass:
            x: int
            y: int
        """,
    )

    with StringIO() as string, contextlib.redirect_stdout(string):
        print_function_info(extracted_functions, with_private=False)
        output = string.getvalue()

    assert output.strip() == expected_output.strip()
