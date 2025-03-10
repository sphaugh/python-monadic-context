"""
# The MIT License

Copyright 2013-2022, Dag Brattli, Microsoft Corp., and Contributors.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from collections.abc import Callable
from functools import reduce
from typing import Any, overload


@overload
def compose[A, B](__op1: Callable[[A], B]) -> Callable[[A], B]: ...


@overload
def compose[A, B, C](
    __op1: Callable[[A], B], __op2: Callable[[B], C]
) -> Callable[[A], C]: ...


@overload
def compose[A, B, C, D](
    __op1: Callable[[A], B],
    __op2: Callable[[B], C],
    __op3: Callable[[C], D],
) -> Callable[[A], D]: ...


@overload
def compose[A, B, C, D, E](
    __op1: Callable[[A], B],
    __op2: Callable[[B], C],
    __op3: Callable[[C], D],
    __op4: Callable[[D], E],
) -> Callable[[A], E]: ...


@overload
def compose[A, B, C, D, E, F](
    __op1: Callable[[A], B],
    __op2: Callable[[B], C],
    __op3: Callable[[C], D],
    __op4: Callable[[D], E],
    __op5: Callable[[E], F],
) -> Callable[[A], F]: ...


@overload
def compose[A, B, C, D, E, F, G](
    __op1: Callable[[A], B],
    __op2: Callable[[B], C],
    __op3: Callable[[C], D],
    __op4: Callable[[D], E],
    __op5: Callable[[E], F],
    __op6: Callable[[F], G],
) -> Callable[[A], G]: ...


def compose(*operators: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose multiple operators left to right.

    Composes zero or more operators into a functional composition. The
    operators are composed to left to right. A composition of zero
    operators gives back the source.

    Examples:
        >>> pipe()(source) == source
        >>> pipe(f)(source) == f(source)
        >>> pipe(f, g)(source) == g(f(source))
        >>> pipe(f, g, h)(source) == h(g(f(source)))
        ...

    Returns:
        The composed observable.
    """

    def _compose(source: Any) -> Any:
        return reduce(lambda obs, op: op(obs), operators, source)

    return _compose


@overload
def pipe[A](value: A) -> A: ...


@overload
def pipe[A, B](__value: A, __fn1: Callable[[A], B]) -> B: ...


@overload
def pipe[A, B, C](
    __value: A,
    __fn1: Callable[[A], B],
    __fn2: Callable[[B], C],
) -> C: ...


@overload
def pipe[A, B, C, D](
    __value: A,
    __fn1: Callable[[A], B],
    __fn2: Callable[[B], C],
    __fn3: Callable[[C], D],
) -> D: ...


@overload
def pipe[A, B, C, D, E](
    __value: A,
    __fn1: Callable[[A], B],
    __fn2: Callable[[B], C],
    __fn3: Callable[[C], D],
    __fn4: Callable[[D], E],
) -> E: ...


@overload
def pipe[A, B, C, D, E, F](
    __value: A,
    __fn1: Callable[[A], B],
    __fn2: Callable[[B], C],
    __fn3: Callable[[C], D],
    __fn4: Callable[[D], E],
    __fn5: Callable[[E], F],
) -> F: ...


@overload
def pipe[A, B, C, D, E, F, G](
    __value: A,
    __fn1: Callable[[A], B],
    __fn2: Callable[[B], C],
    __fn3: Callable[[C], D],
    __fn4: Callable[[D], E],
    __fn5: Callable[[E], F],
    __fn6: Callable[[F], G],
) -> G: ...


@overload
def pipe[A, B, C, D, E, F, G, H](
    __value: A,
    __fn1: Callable[[A], B],
    __fn2: Callable[[B], C],
    __fn3: Callable[[C], D],
    __fn4: Callable[[D], E],
    __fn5: Callable[[E], F],
    __fn6: Callable[[F], G],
    __fn7: Callable[[G], H],
) -> H: ...


@overload
def pipe[A, B, C, D, E, F, G, H, T](
    __value: A,
    __fn1: Callable[[A], B],
    __fn2: Callable[[B], C],
    __fn3: Callable[[C], D],
    __fn4: Callable[[D], E],
    __fn5: Callable[[E], F],
    __fn6: Callable[[F], G],
    __fn7: Callable[[G], H],
    __fn8: Callable[[H], T],
) -> T: ...


@overload
def pipe[A, B, C, D, E, F, G, H, T, J](
    __value: A,
    __fn1: Callable[[A], B],
    __fn2: Callable[[B], C],
    __fn3: Callable[[C], D],
    __fn4: Callable[[D], E],
    __fn5: Callable[[E], F],
    __fn6: Callable[[F], G],
    __fn7: Callable[[G], H],
    __fn8: Callable[[H], T],
    __fn9: Callable[[T], J],
) -> J: ...


def pipe(value: Any, *fns: Callable[[Any], Any]) -> Any:
    """Functional pipe (`|>`)

    Allows the use of function argument on the left side of the
    function.

    Example:
        >>> pipe(x, fn) == __fn(x)  # Same as x |> fn
        >>> pipe(x, fn, gn) == gn(fn(x))  # Same as x |> fn |> gn
        ...
    """

    return compose(*fns)(value)


__all__ = ["pipe", "compose"]

