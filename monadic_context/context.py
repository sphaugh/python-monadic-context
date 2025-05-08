from __future__ import annotations

import itertools
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Generator, Generic, TypeVar

if sys.version_info >= (3, 11):
    from typing import Never, ParamSpec, Concatenate
else:
    from typing_extensions import Never, ParamSpec, Concatenate

from .defer import defer
from .pipe import pipe

_T = TypeVar("_T")
_A = TypeVar("_A")
_B = TypeVar("_B")
_U = TypeVar("_U")
_R = TypeVar("_R")
_P = ParamSpec("_P")
_T_contra = TypeVar("_T_contra", contravariant=True)
_T_co = TypeVar("_T_co", covariant=True)


RequiresContext = Callable[["Context[_T]"], _A]


def pure(a: _A) -> RequiresContext[Never, _A]:
    """Create a pure context-requiring function that returns a value."""

    def _inner(_: Context[Never]) -> _A:
        return a

    return _inner


@defer
def map(
    ma: RequiresContext[_T, _A],
    f: Callable[[_A], _B],
) -> RequiresContext[_T, _B]:
    @wraps(f)
    def _inner(c: Context[_T]) -> _B:
        return f(c.run(ma))

    return _inner


@defer
def bind(
    ma: RequiresContext[_T, _A],
    f: Callable[[_A], RequiresContext[_U, _B]],
) -> RequiresContext[_T | _U, _B]:
    @wraps(f)
    def _inner(c: Context[_T | _U]) -> _B:
        a = c.run(ma)

        return c.run(f(a))

    return _inner


@defer
def apply(
    mab: RequiresContext[_T, Callable[[_A], _B]],
    ma: RequiresContext[_U, _A],
) -> RequiresContext[_T | _U, _B]:
    @wraps(mab)
    def _inner(c: Context[_T | _U]) -> _B:
        a = c.run(ma)

        return c.run(mab)(a)

    return _inner


@defer
def then(
    ma: RequiresContext[_T, _A],
    mb: RequiresContext[_T, _B],
) -> RequiresContext[_T, _B]:
    return pipe(
        mb,
        map(lambda _: lambda b: b),
        apply(ma),
    )


@defer
def traverse(
    xs: list[_A],
    f: Callable[[_A], RequiresContext[_T, _B]],
) -> RequiresContext[_T, list[_B]]:
    @wraps(f)
    def _inner(c: Context[_T]) -> list[_B]:
        return [c.run(f(x)) for x in xs]

    return _inner


def ask(t: Tag[_T]) -> RequiresContext[_T, _T]:
    def _inner(c: Context[_T]):
        return c._unsafe_map[t._id]

    return _inner


@defer
def asks(
    f: Callable[[_T], _A],
    t: Tag[_T],
) -> RequiresContext[_T, _A]:
    return pipe(ask(t), map(f))


@defer
def with_service(
    f: Callable[Concatenate[_T, _P], _A],
    t: Tag[_T],
) -> Callable[_P, RequiresContext[_T, _A]]:
    @wraps(f)
    def _inner(*args, **kwargs) -> RequiresContext[_T, _A]:
        return lambda c: f(c._unsafe_map[t._id], *args, **kwargs)

    return _inner


@dataclass(frozen=True)
class Context(Generic[_T_contra]):
    _unsafe_map: dict[str, Any] = field(default_factory=dict)

    def run(self, f: RequiresContext[_T_contra, _A]) -> _A:
        return f(self)

    def join(self, other: Context[_U]) -> Context[_T_contra | _U]:
        return Context(
            {**self._unsafe_map, **other._unsafe_map},
        )

    def extend(self, t: Tag[_U], service: _U) -> Context[_T_contra | _U]:
        return Context({**self._unsafe_map, t._id: service})


@defer
def of(service: _T, t: Tag[_T]) -> Context[_T]:
    """Create a new context with a single service."""

    return Context({t._id: service})


def from_dict(services: dict[Tag[_T], _T]) -> Context[_T]:
    """Create a context from a dictionary of tag to service mappings."""

    return from_pairs(*services.items())


def from_pairs(*pairs: tuple[Tag[_T], _T]) -> Context[_T]:
    """Create a context from multiple (tag, service) pairs."""

    return Context({t._id: service for t, service in pairs})


ServiceGenerator = Callable[_P, Generator["Tag[_R]", _R, _A]]


def requires(
    f: ServiceGenerator[_P, _R, _A],
) -> Callable[_P, RequiresContext[_R, _A]]:
    """Decorator to mark a function as requiring context.
    This allows the function to yield tags and receive values from the context.
    """

    @wraps(f)
    def _inner(c: Context[_R], *args: _P.args, **kwargs: _P.kwargs) -> _A:
        gen = f(*args, **kwargs)
        value = None
        while True:
            try:
                tag = gen.send(value) if value is not None else next(gen)
                value = c._unsafe_map[tag._id]
            except StopIteration as e:
                return e.value
            except KeyError as e:
                raise KeyError(
                    f"Tag {e} not found in context. Available tags: {list(c._unsafe_map.keys())}"
                ) from e

    return lambda *args, **kwargs: lambda c: _inner(c, *args, **kwargs)


def use(tag: Tag[_T]) -> Generator[Tag[_T], _T, _T]:
    return (yield tag)


def genid():
    counter = itertools.count()
    return lambda: str(next(counter))


@dataclass(frozen=True)
class Tag(Generic[_T_co]):
    """Type-safe identifier for a dependency in a context.

    Used to request and provide dependencies of a specific type.
    """

    _id: str = field(default_factory=genid())

    @classmethod
    def new(cls, id: str) -> Tag[_T_co]:
        return cls(id)
