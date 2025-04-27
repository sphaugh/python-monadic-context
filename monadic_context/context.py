from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Concatenate, Generator, Generic, Never, TypeVar

from .defer import defer
from .pipe import pipe


type RequiresContext[T, A] = Callable[[Context[T]], A]


def pure[A](a: A) -> RequiresContext[Never, A]:
    """Create a pure context-requiring function that returns a value."""

    def _inner(_: Context[Never]) -> A:
        return a

    return _inner


@defer
def map[T, A, B](
    ma: RequiresContext[T, A],
    f: Callable[[A], B],
) -> RequiresContext[T, B]:
    @wraps(f)
    def _inner(c: Context[T]) -> B:
        return f(c.run(ma))

    return _inner


@defer
def bind[T, A, U, B](
    ma: RequiresContext[T, A],
    f: Callable[[A], RequiresContext[U, B]],
) -> RequiresContext[T | U, B]:
    @wraps(f)
    def _inner(c: Context[T | U]) -> B:
        a = c.run(ma)

        return c.run(f(a))

    return _inner


@defer
def apply[T, A, U, B](
    mab: RequiresContext[U, Callable[[A], B]],
    ma: RequiresContext[T, A],
) -> RequiresContext[T | U, B]:
    @wraps(mab)
    def _inner(c: Context[T | U]) -> B:
        a = c.run(ma)

        return c.run(mab)(a)

    return _inner


@defer
def then[T, A, B](
    ma: RequiresContext[T, A],
    mb: RequiresContext[T, B],
) -> RequiresContext[T, B]:
    return pipe(
        mb,
        map(lambda _: lambda b: b),
        apply(ma),
    )


@defer
def traverse[T, A, B](
    xs: list[A],
    f: Callable[[A], RequiresContext[T, B]],
) -> RequiresContext[T, list[B]]:
    @wraps(f)
    def _inner(c: Context[T]) -> list[B]:
        return [c.run(f(x)) for x in xs]

    return _inner


def ask[T](t: Tag[T]) -> RequiresContext[T, T]:
    def _inner(c: Context[T]):
        return c._unsafe_map[t._id]

    return _inner


@defer
def asks[T, A](
    f: Callable[[T], A],
    t: Tag[T],
) -> RequiresContext[T, A]:
    return pipe(ask(t), map(f))


@defer
def with_service[T, **P, A](
    f: Callable[Concatenate[T, P], A],
    t: Tag[T],
) -> Callable[P, RequiresContext[T, A]]:
    @wraps(f)
    def _inner(*args: P.args, **kwargs: P.kwargs) -> RequiresContext[T, A]:
        return lambda c: f(c._unsafe_map[t._id], *args, **kwargs)

    return _inner


_T_contra = TypeVar("_T_contra", contravariant=True)


@dataclass(frozen=True)
class Context(Generic[_T_contra]):
    _unsafe_map: dict[str, Any] = field(default_factory=dict)

    def run[A](self, f: RequiresContext[_T_contra, A]) -> A:
        return f(self)

    def join[U](self, other: Context[U]) -> Context[_T_contra | U]:
        return Context(
            {**self._unsafe_map, **other._unsafe_map},
        )

    def extend[U](self, t: Tag[U], service: U) -> Context[_T_contra | U]:
        return Context({**self._unsafe_map, t._id: service})


@defer
def of[T](service: T, t: Tag[T]) -> Context[T]:
    """Create a new context with a single service."""

    return Context({t._id: service})


def from_dict[T](services: dict[Tag[T], T]) -> Context[T]:
    """Create a context from a dictionary of tag to service mappings."""

    return from_pairs(*services.items())


def from_pairs[T](*pairs: tuple[Tag[T], T]) -> Context[T]:
    """Create a context from multiple (tag, service) pairs."""

    return Context({t._id: service for t, service in pairs})


type ServiceGenerator[**P, R, A] = Callable[P, Generator[Tag[R], R, A]]


def requires[**P, R, A](
    f: ServiceGenerator[P, R, A],
) -> Callable[P, RequiresContext[R, A]]:
    """Decorator to mark a function as requiring context.
    This allows the function to yield tags and receive values from the context.
    """

    @wraps(f)
    def _inner(c: Context[R], *args: P.args, **kwargs: P.kwargs) -> A:
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


def use[T](tag: Tag[T]) -> Generator[Tag[T], T, T]:
    return (yield tag)


def genid():
    counter = itertools.count()
    return lambda: str(next(counter))


@dataclass(frozen=True)
class Tag[T]:
    _id: str = field(default_factory=genid())

    @classmethod
    def new(cls, id: str) -> Tag[T]:
        return cls(id)
