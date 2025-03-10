from collections.abc import Callable
from functools import wraps
from typing import Concatenate


def defer[A, **P, B](
    f: Callable[Concatenate[A, P], B],
) -> Callable[P, Callable[[A], B]]:
    @wraps(f)
    def _inner(*args: P.args, **kwargs: P.kwargs) -> Callable[[A], B]:
        return lambda a: f(a, *args, **kwargs)

    return _inner
