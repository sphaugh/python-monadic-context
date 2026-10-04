from __future__ import annotations

import itertools
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Generator, Generic, Protocol, TypeVar, overload

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
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")
_T3 = TypeVar("_T3")
_T4 = TypeVar("_T4")
_T5 = TypeVar("_T5")
_T6 = TypeVar("_T6")
_T7 = TypeVar("_T7")
_T8 = TypeVar("_T8")
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
        f = c.run(mab)

        return f(c.run(ma))

    return _inner


@defer
def then(
    ma: RequiresContext[_T, _A],
    mb: RequiresContext[_U, _B],
) -> RequiresContext[_T | _U, _B]:
    """Run ``ma`` for its effects, then run ``mb`` and return its value."""

    def _inner(c: Context[_T | _U]) -> _B:
        c.run(ma)
        return c.run(mb)

    return _inner


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
    def _inner(c: Context[_T]) -> _T:
        return c._get(t)

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
        return lambda c: f(c._get(t), *args, **kwargs)

    return _inner


@dataclass(frozen=True)
class Context(Generic[_T_contra]):
    _unsafe_map: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def of(cls, t: _ExactTag[_T], service: _T) -> Context[_T]:
        """A context holding a single service.

        ``t`` is typed through an invariant view of ``Tag`` so the service is
        checked against the tag's type rather than widened to a union with it.
        """

        return Context({t._id: service})

    def run(self, f: RequiresContext[_T_contra, _A]) -> _A:
        return f(self)

    def _get(self, t: Tag[_A]) -> _A:
        try:
            return self._unsafe_map[t._id]
        except KeyError as e:
            raise KeyError(
                f"Tag {t._id!r} not found in context. Available tags: {list(self._unsafe_map)}"
            ) from e

    def join(self, other: Context[_U]) -> Context[_T_contra | _U]:
        return Context(
            {**self._unsafe_map, **other._unsafe_map},
        )

    def extend(self, t: _ExactTag[_U], service: _U) -> Context[_T_contra | _U]:
        return Context({**self._unsafe_map, t._id: service})


of = Context.of


@overload
def from_pairs(
    p1: tuple[_ExactTag[_T1], _T1],
    /,
) -> Context[_T1]: ...


@overload
def from_pairs(
    p1: tuple[_ExactTag[_T1], _T1],
    p2: tuple[_ExactTag[_T2], _T2],
    /,
) -> Context[_T1 | _T2]: ...


@overload
def from_pairs(
    p1: tuple[_ExactTag[_T1], _T1],
    p2: tuple[_ExactTag[_T2], _T2],
    p3: tuple[_ExactTag[_T3], _T3],
    /,
) -> Context[_T1 | _T2 | _T3]: ...


@overload
def from_pairs(
    p1: tuple[_ExactTag[_T1], _T1],
    p2: tuple[_ExactTag[_T2], _T2],
    p3: tuple[_ExactTag[_T3], _T3],
    p4: tuple[_ExactTag[_T4], _T4],
    /,
) -> Context[_T1 | _T2 | _T3 | _T4]: ...


@overload
def from_pairs(
    p1: tuple[_ExactTag[_T1], _T1],
    p2: tuple[_ExactTag[_T2], _T2],
    p3: tuple[_ExactTag[_T3], _T3],
    p4: tuple[_ExactTag[_T4], _T4],
    p5: tuple[_ExactTag[_T5], _T5],
    /,
) -> Context[_T1 | _T2 | _T3 | _T4 | _T5]: ...


@overload
def from_pairs(
    p1: tuple[_ExactTag[_T1], _T1],
    p2: tuple[_ExactTag[_T2], _T2],
    p3: tuple[_ExactTag[_T3], _T3],
    p4: tuple[_ExactTag[_T4], _T4],
    p5: tuple[_ExactTag[_T5], _T5],
    p6: tuple[_ExactTag[_T6], _T6],
    /,
) -> Context[_T1 | _T2 | _T3 | _T4 | _T5 | _T6]: ...


@overload
def from_pairs(
    p1: tuple[_ExactTag[_T1], _T1],
    p2: tuple[_ExactTag[_T2], _T2],
    p3: tuple[_ExactTag[_T3], _T3],
    p4: tuple[_ExactTag[_T4], _T4],
    p5: tuple[_ExactTag[_T5], _T5],
    p6: tuple[_ExactTag[_T6], _T6],
    p7: tuple[_ExactTag[_T7], _T7],
    /,
) -> Context[_T1 | _T2 | _T3 | _T4 | _T5 | _T6 | _T7]: ...


@overload
def from_pairs(
    p1: tuple[_ExactTag[_T1], _T1],
    p2: tuple[_ExactTag[_T2], _T2],
    p3: tuple[_ExactTag[_T3], _T3],
    p4: tuple[_ExactTag[_T4], _T4],
    p5: tuple[_ExactTag[_T5], _T5],
    p6: tuple[_ExactTag[_T6], _T6],
    p7: tuple[_ExactTag[_T7], _T7],
    p8: tuple[_ExactTag[_T8], _T8],
    /,
) -> Context[_T1 | _T2 | _T3 | _T4 | _T5 | _T6 | _T7 | _T8]: ...


def from_pairs(*pairs: tuple[_ExactTag[Any], Any]) -> Context[Any]:
    """Create a context from (tag, service) pairs, each service checked against its tag."""

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
        try:
            tag = next(gen)
            while True:
                tag = gen.send(c._get(tag))
        except StopIteration as e:
            return e.value

    return lambda *args, **kwargs: lambda c: _inner(c, *args, **kwargs)


def use(tag: Tag[_T]) -> Generator[Tag[_T], _T, _T]:
    return (yield tag)


def genid():
    counter = itertools.count()
    return lambda: f"_anon{next(counter)}"


class _ExactTag(Protocol[_T]):
    """Invariant structural view of ``Tag``.

    ``Tag`` is covariant so generators can yield several tags under one type
    variable. In ``of``-style constructors that would let a mismatched value
    widen the inferred type instead of being rejected; matching the tag
    against this protocol pins the type variable exactly. ``use`` has the
    type variable in both a covariant and a contravariant position, which is
    what makes the protocol invariant. Any ``Tag`` satisfies it unchanged.
    """

    @property
    def _id(self) -> str: ...

    def use(self) -> Generator[Tag[_T], _T, _T]: ...


@dataclass(frozen=True)
class Tag(Generic[_T_co]):
    """Type-safe identifier for a dependency in a context.

    Used to request and provide dependencies of a specific type.
    """

    _id: str = field(default_factory=genid())

    @classmethod
    def new(cls, id: str) -> Tag[_T_co]:
        return cls(id)

    def use(self) -> Generator[Tag[_T_co], _T_co, _T_co]:
        return use(self)
