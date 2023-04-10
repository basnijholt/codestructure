# type: ignore
class MyClass:
    my_attr: str
    _my_private_attr: int

    def my_method(self, arg1: int) -> bool:
        """My docstring."""
        x = 1 + 2
        ...


def my_function(arg2: float) -> None:
    arg2 = arg2 + 1
    return arg2**2


def _private_function():
    """My private function."""
    x = 1 + 2
    y = x + 4
    return y
