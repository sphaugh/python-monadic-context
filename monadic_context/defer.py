from collections.abc import Callable
from functools import wraps
import sys
from typing import TypeVar

if sys.version_info >= (3, 10):
    from typing import Concatenate, ParamSpec
else:
    from typing_extensions import Concatenate, ParamSpec

_A = TypeVar("_A")
_B = TypeVar("_B")
_P = ParamSpec("_P")


def defer(
    f: Callable[Concatenate[_A, _P], _B],
) -> Callable[_P, Callable[[_A], _B]]:
    @wraps(f)
    def _inner(*args: _P.args, **kwargs: _P.kwargs) -> Callable[[_A], _B]:
        return lambda a: f(a, *args, **kwargs)

    return _inner
