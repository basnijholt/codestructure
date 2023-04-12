"""CodeStructure: A Python package for extracting code structure information from Python modules."""
from __future__ import annotations

import argparse
import ast
import contextlib
import io
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyperclip
import rich
from rich.console import Console
from rich.syntax import Syntax


def parse_module(
    file_path: str | Path | None = None,
    source_code: str | None = None,
) -> ast.Module:
    """Parse the source code of a Python module.

    Parameters
    ----------
    file_path
        The path to the Python module file.
    source_code
        The source code of the Python module as a string.

    Returns
    -------
    The AST representation of the module.
    """
    if not file_path and not source_code:  # pragma: no cover
        msg = "Either 'file_path' or 'source_code' must be provided."
        raise ValueError(msg)

    if file_path:
        with Path(file_path).open() as f:
            source_code = f.read()
    assert source_code is not None
    tree = ast.parse(source_code)
    add_parent_list(tree)
    return tree


@dataclass
class Parameter:
    """A function parameter."""

    name: str
    param_type: str | None
    default_value: Any | None
    kw_only: bool = False


@dataclass
class Function:
    """A function."""

    name: str
    docstring: str | None
    decorator: str | None
    parameters: list[Parameter]
    return_type: str | None

    @classmethod
    def from_node(
        cls: type[Function],
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> Function:
        """Create a Function object from an AST node."""
        function_name = node.name
        docstring = ast.get_docstring(node)
        decorator_name = Class.get_decorator_name(node)
        parameters = Function.get_parameters(node)
        return_type = ast.unparse(node.returns) if node.returns else None
        return Function(
            name=function_name,
            docstring=docstring,
            decorator=decorator_name,
            parameters=parameters,
            return_type=return_type,
        )

    @staticmethod
    def get_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Parameter]:
        """Get the parameters of a function.

        Parameters
        ----------
        node
            The AST node of the function.
        """
        parameters = []

        # Process positional arguments
        num_defaults = len(node.args.defaults)
        num_positional_args = len(node.args.args) - num_defaults

        for _i, arg in enumerate(node.args.args[:num_positional_args]):
            param_type = ast.unparse(arg.annotation) if arg.annotation else None
            parameters.append(
                Parameter(
                    name=arg.arg,
                    param_type=param_type,
                    default_value=None,
                    kw_only=False,
                ),
            )

        # Process positional arguments with default values
        for i, arg in enumerate(node.args.args[num_positional_args:]):
            default_index = i
            expr = node.args.defaults[default_index]
            try:
                default_value = ast.literal_eval(expr)
            except ValueError:
                default_value = ast.unparse(expr)

            param_type = ast.unparse(arg.annotation) if arg.annotation else None
            parameters.append(
                Parameter(
                    name=arg.arg,
                    param_type=param_type,
                    default_value=default_value,
                    kw_only=False,
                ),
            )

        # Process keyword-only arguments
        for i, arg in enumerate(node.args.kwonlyargs):
            default_value = None
            if node.args.kw_defaults[i] is not None:
                expr = node.args.kw_defaults[i]  # type: ignore[assignment]
                assert expr is not None
                try:
                    default_value = ast.literal_eval(expr)
                except ValueError:
                    default_value = ast.unparse(expr)

            param_type = ast.unparse(arg.annotation) if arg.annotation else None
            parameters.append(
                Parameter(
                    name=arg.arg,
                    param_type=param_type,
                    default_value=default_value,
                    kw_only=True,
                ),
            )

        return parameters


@dataclass
class Class:
    """A class."""

    class_name: str
    attributes: list[tuple[str, str | None]]
    functions: list[Function] = field(default_factory=list)
    docstring: str | None = None
    decorator: str | None = None

    @classmethod
    def from_node(cls: type[Class], node: ast.ClassDef) -> Class:
        """Create a Class object from an AST node."""
        class_attributes = [
            (
                stmt.target.id,
                ast.unparse(stmt.annotation) if stmt.annotation else None,
            )
            for stmt in node.body
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
        ]
        decorator_name = Class.get_decorator_name(node)
        class_docstring = ast.get_docstring(node)
        return cls(
            class_name=node.name,
            docstring=class_docstring,
            attributes=class_attributes,
            decorator=decorator_name,
        )

    @staticmethod
    def get_decorator_name(
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    ) -> str | None:
        """Get the name of the decorator of a function or class."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name | ast.Attribute):
                return ast.unparse(decorator)
        return None

    @staticmethod
    def get_class_name(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_names: list[str],
    ) -> str | None:
        """Get the name of the class that a function is a method of."""
        for cls in class_names[::-1]:
            if any(
                isinstance(parent, ast.ClassDef) and parent.name == cls
                for parent in node.parent_list  # type: ignore[attr-defined, union-attr]
            ):
                return cls
        return None


@dataclass
class ExtractedInfo:
    """The information about classes and functions in a Python module."""

    classes: list[Class] = field(default_factory=list)
    functions: list[Function] = field(default_factory=list)

    @classmethod
    def from_ast(cls: type[ExtractedInfo], tree: ast.Module) -> ExtractedInfo:
        """Extract information about classes and functions from the AST of a Python module.

        Parameters
        ----------
        tree
            The AST representation of the module.

        Returns
        -------
            An ExtractedInfo object containing information about the classes and functions in the module.
        """
        result = ExtractedInfo()
        class_names: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_names.append(node.name)
                result.classes.append(Class.from_node(node))

            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if any(
                    isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef)
                    for parent in node.parent_list  # type: ignore[union-attr]
                ):
                    continue

                class_name = Class.get_class_name(node, class_names)
                func = Function.from_node(node)
                if class_name:
                    class_index = next(
                        i
                        for i, class_info in enumerate(result.classes)
                        if class_info.class_name == class_name
                    )
                    result.classes[class_index].functions.append(func)
                else:
                    result.functions.append(func)
        return result

    def print(  # noqa: A003
        self: ExtractedInfo,
        *,
        with_private: bool = True,
    ) -> None:
        """Print the information about classes and functions in a Python module."""

        def format_function(function: Function, indent_level: int) -> str:
            indent = " " * indent_level
            decorator = f"{indent}@{function.decorator}\n" if function.decorator else ""
            signature = f"{indent}def {function.name}("

            params = []
            for param in function.parameters:
                param_str = (
                    f"{param.name}: {param.param_type}"
                    if param.param_type
                    else param.name
                )
                if param.default_value is not None:
                    param_str += f" = {param.default_value}"
                if param.kw_only:
                    param_str = "*, " + param_str
                params.append(param_str)

            signature += ", ".join(params)
            signature += (
                f") -> {function.return_type if function.return_type else 'None'}:"
            )
            indent_docs = indent + (" " * 4)
            docstring = textwrap.indent(
                f'"""{function.docstring}"""' if function.docstring else "...",
                indent_docs,
            )

            return f"{decorator}{signature}\n{docstring}\n"

        for class_info in self.classes:
            if class_info.decorator:
                print(f"@{class_info.decorator}")
            print(f"class {class_info.class_name}:")

            attrs = [
                (attr_name, attr_type)
                for attr_name, attr_type in class_info.attributes
                if with_private or not _is_private(attr_name)
            ]
            methods = [
                (method.name, method)
                for method in class_info.functions
                if with_private or not _is_private(method.name)
            ]

            if class_info.docstring:
                print(f'    """{class_info.docstring}"""')
            elif not attrs and not methods:
                print("    ...")

            for attr_name, attr_type in attrs:
                print(
                    f"    {attr_name}: {attr_type}"
                    if attr_type
                    else f"    {attr_name}",
                )

            for _method_name, method in methods:
                print(format_function(method, 4))
            print()

        for function in self.functions:
            if not with_private and _is_private(function.name):
                continue
            print(format_function(function, 0))
            print()


def _is_private(name: str) -> bool:
    return name.startswith("_")


def add_parent_list(tree: ast.Module) -> None:
    """Add the parent list attribute to each node in the AST.

    This attribute is a list of all the ancestors of the node.

    Parameters
    ----------
    tree
        The AST representation of the module.
    """
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent_list = [*getattr(node, "parent_list", []), node]  # type: ignore[attr-defined]
            add_parent_list(child)  # type: ignore[arg-type]


def print_syntax_with_rich(
    s: str,
    *,
    line_numbers: bool = False,
) -> None:  # pragma: no cover
    """Pretty-print Python code using the rich library.

    Parameters
    ----------
    s
        A string containing Python code.
    line_numbers
        Whether to print line numbers.
    """
    syntax = Syntax(
        s,
        "python",
        theme="monokai",
        line_numbers=line_numbers,
        word_wrap=True,
    )
    console = Console(soft_wrap=False)
    console.print(syntax)


def main() -> None:
    """Parse the command line arguments and print the function info."""
    parser = argparse.ArgumentParser(
        description="Analyze the code structure of a Python file.",
    )
    parser.add_argument("module_file_path", type=str, help="Path to the Python file.")
    parser.add_argument(
        "--no-private",
        action="store_true",
        help="Do not print private functions.",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Do not copy the output to the clipboard.",
    )
    parser.add_argument(
        "--backticks",
        action="store_true",
        help="Use backticks for code blocks.",
    )
    parser.add_argument(
        "--no-rich",
        action="store_true",
        help="Do not use rich to print the output.",
    )
    parser.add_argument(
        "--line-numbers",
        action="store_true",
        help="Print line numbers for the code blocks.",
    )
    args = parser.parse_args()

    tree = parse_module(args.module_file_path)
    function_info = ExtractedInfo.from_ast(tree)

    with io.StringIO() as string, contextlib.redirect_stdout(string):
        ExtractedInfo.print(function_info, with_private=not args.no_private)
        output = string.getvalue()

    if args.backticks:  # pragma: no cover
        output = "```python\n" + output + "```"
    if args.no_rich:
        print(output)
    else:  # pragma: no cover
        print_syntax_with_rich(output, line_numbers=args.line_numbers)

    if not args.no_copy:  # pragma: no cover
        try:
            pyperclip.copy(output)
        except pyperclip.PyperclipException:
            rich.print("[red bold]⚠️ Could not copy to clipboard.[/]")


if __name__ == "__main__":
    main()
