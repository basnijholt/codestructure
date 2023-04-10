# 🏗️ CodeStructure

CodeStructure is a Python package that analyzes the structure of a Python file and extracts information about its classes, functions, and their associated attributes.
It is particularly useful for understanding and documenting complex codebases.

## 🌟 Features

- Extract class and function signatures
- Extract class attributes
- Extract function parameters and their types
- Extract function return types
- Extract decorators and docstrings
- Display the extracted information in a human-readable format

## 📦 Installation

You can install CodeStructure via pip:

```bash
pip install codestructure
```

## 📚 Usage

To use CodeStructure, simply run the script with the path to the Python file you want to analyze:

```bash
codestructure path/to/your/python_file.py
```

The script will output the analyzed code structure and copy it to the clipboard if the `pyperclip` package is installed.

## 📝 Example

Given a Python file with the following content:

```python
class MyClass:
    my_attr: str

    def my_method(self, arg1: int) -> bool:
        """My docstring."""
        a = 1 + 1
        ...

def my_function(arg2: float) -> None:
    arg2 = arg2 + 1
    ...
```

CodeStructure will output:

```python
class MyClass:
    my_attr: str

    def my_method(self, arg1: int) -> bool:
        """My docstring."""

def my_function(arg2: float) -> None:
    ...
```

## 👥 Contributing

We welcome contributions to CodeStructure! If you find a bug or have a feature request, please create an issue on the [GitHub repository](https://github.com/basnijholt/codestructure). If you would like to contribute code, please fork the repository and submit a pull request.

## 📄 License

CodeStructure is released under the Apache 2.0 License. For more information, please see the [LICENSE](LICENSE) file.
