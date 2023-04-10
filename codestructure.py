import argparse
import ast
import contextlib
import subprocess
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def parse_module_file(file_path: str) -> ast.Module:
    """Parse the source code of a Python module.

    Parameters
    ----------
    file_path
        The path to the Python module file.

    Returns
    -------
    The AST representation of the module.
    """
    with Path(file_path).open() as f:
        source_code = f.read()

    return ast.parse(source_code)


@dataclass
class Parameter:
    name: str
    param_type: str | None
    default_value: Any | None


@dataclass
class Function:
    signature: str
    docstring: str | None
    decorator: str | None
    parameters: list[Parameter]
    return_type: str | None


@dataclass
class Class:
    class_name: str
    attributes: list[tuple[str, str | None]]
    functions: dict[str, Function] = field(default_factory=dict)


@dataclass
class ExtractedFunctions:
    classes: dict[str, Class] = field(default_factory=dict)
    functions: dict[str, Function] = field(default_factory=dict)


def extract_function_info(
    tree: ast.Module,
) -> ExtractedFunctions:
    """Extract information about classes and functions from the AST of a Python module.

    Parameters
    ----------
    tree
        The AST representation of the module.

    Returns
    -------
        An ExtractedFunctions object containing information about the classes and functions in the module.
    """
    result = ExtractedFunctions()
    class_names: list[str] = []

    def get_class_name(node: ast.FunctionDef) -> str | None:
        for cls in class_names[::-1]:
            if any(
                isinstance(parent, ast.ClassDef) and parent.name == cls
                for parent in node.parent_list
            ):
                return cls
        return None

    def get_decorator_name(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str | None:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name | ast.Attribute):
                return ast.unparse(decorator)
        return None

    def get_parameters(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[Parameter]:
        parameters = []
        for arg in node.args.args:
            default_value = None
            if arg.arg in node.args.kw_defaults:
                default_value = ast.literal_eval(node.args.kw_defaults[arg.arg])
            param_type = ast.unparse(arg.annotation) if arg.annotation else None
            parameters.append(
                Parameter(
                    name=arg.arg,
                    param_type=param_type,
                    default_value=default_value,
                ),
            )
        return parameters

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_names.append(node.name)
            class_attributes = [
                (
                    stmt.target.id,
                    ast.unparse(stmt.annotation) if stmt.annotation else None,
                )
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            ]
            result.classes[node.name] = Class(
                class_name=node.name,
                attributes=class_attributes,
            )

        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if any(
                isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef)
                for parent in node.parent_list
            ):
                continue

            function_name = node.name
            docstring = ast.get_docstring(node)
            class_name = get_class_name(node)
            decorator_name = get_decorator_name(node)
            parameters = get_parameters(node)
            return_type = ast.unparse(node.returns) if node.returns else None
            kw = {
                "docstring": docstring,
                "decorator": decorator_name,
                "parameters": parameters,
                "return_type": return_type,
            }

            if class_name:
                function = Function(
                    signature=f"{class_name}.{function_name}",
                    **kw,
                )
                result.classes[class_name].functions[function_name] = function
            else:
                function = Function(
                    signature=function_name,
                    **kw,
                )
                result.functions[function_name] = function
    return result


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
            child.parent_list = [*getattr(node, "parent_list", []), node]
            add_parent_list(child)


def print_function_info(function_info: ExtractedFunctions) -> None:
    """Print the information about classes and functions in a Python module."""

    def format_function(function: Function, indent_level: int) -> str:
        indent = " " * indent_level
        decorator = f"{indent}@{function.decorator}\n" if function.decorator else ""
        signature = f"{indent}def {function.signature}("

        params = []
        for param in function.parameters:
            param_str = (
                f"{param.name}: {param.param_type}" if param.param_type else param.name
            )
            if param.default_value is not None:
                param_str += f"={param.default_value}"
            params.append(param_str)

        signature += ", ".join(params)
        signature += f") -> {function.return_type if function.return_type else 'None'}:"
        indent_docs = indent + (" " * 4)
        docstring = textwrap.indent(
            f'"""{function.docstring}"""' if function.docstring else "...",
            indent_docs,
        )

        return f"{decorator}{signature}\n{docstring}\n"

    for class_name, class_info in function_info.classes.items():
        print(f"class {class_name}:")
        for attr_name, attr_type in class_info.attributes:
            print(f"    {attr_name}: {attr_type}" if attr_type else f"    {attr_name}")

        for _function_name, function in class_info.functions.items():
            print(format_function(function, 4))
        print()

    for name, function in function_info.functions.items():
        name.split(".")[-1]
        print(format_function(function, 0))
        print()


def main() -> None:
    """Parse the command line arguments and print the function info."""
    parser = argparse.ArgumentParser(
        description="Analyze the code structure of a Python file.",
    )
    parser.add_argument("module_file_path", type=str, help="Path to the Python file.")
    args = parser.parse_args()

    tree = parse_module_file(args.module_file_path)
    add_parent_list(tree)
    function_info = extract_function_info(tree)
    import io

    with io.StringIO() as string, contextlib.redirect_stdout(string):
        print_function_info(function_info)
        output = string.getvalue()
    print(output)
    try:
        import pyperclip

        pyperclip.copy(output)
    except ImportError:
        with contextlib.suppress(Exception):
            process = subprocess.Popen(
                "pbcopy", env={"LANG": "en_US.UTF-8"}, stdin=subprocess.PIPE,
            )
            process.communicate(output.encode("utf-8"))
        pass


if __name__ == "__main__":
    main()
