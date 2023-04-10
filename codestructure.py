import ast
import textwrap
import argparse

def parse_module_file(file_path):
    with open(file_path, "r") as f:
        source_code = f.read()

    return ast.parse(source_code)

def extract_function_info(tree):
    result = {"classes": {}, "functions": {}}
    class_names = []

    def get_class_name(node):
        for cls in class_names[::-1]:
            if any(
                isinstance(parent, ast.ClassDef) and parent.name == cls
                for parent in node.parent_list
            ):
                return cls
        return None

    def get_decorator_name(node):
        for decorator in node.decorator_list:
            if isinstance(decorator, (ast.Name, ast.Attribute)):
                return ast.unparse(decorator)
        return None

    def get_parameters(node):
        parameters = []
        for arg in node.args.args:
            default_value = None
            if arg.arg in node.args.kw_defaults:
                default_value = ast.literal_eval(node.args.kw_defaults[arg.arg])
            param_type = ast.unparse(arg.annotation) if arg.annotation else None
            parameters.append((arg.arg, param_type, default_value))
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
            result["classes"][node.name] = {
                "class": node.name,
                "attributes": class_attributes,
            }

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(
                isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
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
                class_functions = result["classes"][class_name].setdefault(
                    "functions", {}
                )
                class_functions[function_name] = {
                    "signature": f"{class_name}.{function_name}",
                    "class": class_name,
                    **kw,
                }
            else:
                result["functions"][function_name] = {"signature": function_name, **kw}

    return result

def add_parent_list(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent_list = getattr(node, "parent_list", []) + [node]
            add_parent_list(child)

def print_function_info(function_info):
    def format_function(function_name, info, indent_level):
        indent = " " * indent_level
        decorator = f'{indent}@{info["decorator"]}\n' if info["decorator"] else ""
        signature = f"{indent}def {function_name}("

        params = []
        for param, param_type, default in info["parameters"]:
            param_str = f"{param}: {param_type}" if param_type else param
            if default is not None:
                param_str += f"={default}"
            params.append(param_str)

        signature += ", ".join(params)
        signature += f") -> {info['return_type'] if info['return_type'] else 'None'}:"
        indent_docs = indent + ("    ")
        docstring = textwrap.indent(
            f'"""{info["docstring"]}"""' if info["docstring"] else "...", indent_docs
        )

        return f"{decorator}{signature}\n{docstring}\n"

    for class_name, class_info in function_info["classes"].items():
        print(f"class {class_name}:")
        for attr_name, attr_type in class_info.get("attributes", []):
            print(f"    {attr_name}: {attr_type}" if attr_type else f"    {attr_name}")

        for function_name, info in class_info.get("functions", {}).items():
            print(format_function(function_name, info, 4))
        print()

    for name, info in function_info["functions"].items():
        method_name = name.split(".")[-1]
        print(format_function(method_name, info, 0))
        print()

def main():
    parser = argparse.ArgumentParser(description="Analyze the code structure of a Python file.")
    parser.add_argument("module_file_path", type=str, help="Path to the Python file.")
    args = parser.parse_args()

    tree = parse_module_file(args.module_file_path)
    add_parent_list(tree)
    function_info = extract_function_info(tree)
    print_function_info(function_info)

if __name__ == "__main__":
    main()

