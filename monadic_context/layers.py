from __future__ import annotations

import sys
from collections.abc import AsyncGenerator, AsyncIterator, Callable, Generator, Iterator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
    asynccontextmanager,
    contextmanager,
)
from dataclasses import dataclass
from functools import wraps
from typing import Any, Generic, Union

if sys.version_info >= (3, 13):
    from typing import Never, ParamSpec, TypeVar
else:
    from typing_extensions import Never, ParamSpec, TypeVar

from .context import Context, Tag, _ExactTag

_T = TypeVar("_T")
_A = TypeVar("_A")
_B = TypeVar("_B")
_C = TypeVar("_C")
_Out = TypeVar("_Out")  # invariant on purpose: lets `then` infer the accumulated output exactly
_In_co = TypeVar("_In_co", covariant=True)
_In = TypeVar("_In", default=Never)  # a layer that requests nothing needs nothing
_P = ParamSpec("_P")

_NO_SERVICE = "layer generator did not yield a service"
_TOO_MANY = "layer generator yielded again after the service"


@dataclass(frozen=True)
class Layer(Generic[_In_co, _Out]):
    """A recipe for building part of a Context, with resource lifecycle.

    Input is covariant: a layer needing less fits where more is available.
    Output is invariant so ``then`` infers the accumulated context exactly.
    """

    _f: Callable[[Context[_In_co]], AbstractContextManager[Context[_Out]]]

    @classmethod
    def of(cls, t: _ExactTag[_T], value: _T) -> Layer[Never, _T]:
        """A layer providing one ready-made value, with no resources."""

        @contextmanager
        def _inner(_: Context[Never]) -> Iterator[Context[_T]]:
            yield Context.of(t, value)

        return Layer(_inner)

    def then(self: Layer[_A, _B], other: Layer[_B, _C]) -> Layer[_A, _B | _C]:
        """Build ``self``, then ``other`` with ``self``'s outputs available.

        Teardown is reverse order. If ``other`` fails to enter, ``self`` is
        released before the exception propagates.
        """

        @contextmanager
        def _inner(ctx: Context[_A]) -> Iterator[Context[_B | _C]]:
            with ExitStack() as stack:
                a_out = stack.enter_context(self._f(ctx))
                b_out = stack.enter_context(other._f(ctx.join(a_out)))
                yield a_out.join(b_out)

        return Layer(_inner)

    def build(
        self: Layer[_A, _B], ctx: Context[_A] = Context()
    ) -> AbstractContextManager[Context[_B]]:
        """Enter the layer; the ``with`` block receives the built context."""

        return self._f(ctx)


def layer(
    t: Tag[_T],
) -> Callable[
    [Callable[_P, Generator[Union[Tag[_In], _T], Any, None]]],
    Callable[_P, Layer[_In, _T]],
]:
    """Define a layer factory from a generator function.

    The decorated function keeps its parameters and returns a ``Layer`` when
    called. Inside, yield tags (``yield from use(tag)`` or ``yield tag``) to
    receive their values from the context. The first non-Tag yield is the
    service; code after it is cleanup, and an exception in the ``with`` body
    is thrown in at that point, exactly like ``contextlib.contextmanager``.
    """

    def decorate(
        f: Callable[_P, Generator[Union[Tag[_In], _T], Any, None]],
    ) -> Callable[_P, Layer[_In, _T]]:
        @wraps(f)
        def factory(*args: _P.args, **kwargs: _P.kwargs) -> Layer[_In, _T]:
            @contextmanager
            def enter(ctx: Context[_In]) -> Iterator[Context[_T]]:
                gen = f(*args, **kwargs)
                try:
                    item = next(gen)
                    while isinstance(item, Tag):
                        item = gen.send(ctx._get(item))
                except StopIteration:
                    raise RuntimeError(_NO_SERVICE) from None
                try:
                    yield Context.of(t, item)
                except BaseException as exc:
                    try:
                        gen.throw(exc)
                    except StopIteration:
                        return  # the layer handled it; suppress, as contextmanager does
                    raise RuntimeError(_TOO_MANY)
                else:
                    try:
                        next(gen)
                    except StopIteration:
                        return
                    raise RuntimeError(_TOO_MANY)

            return Layer(enter)

        return factory

    return decorate


@dataclass(frozen=True)
class AsyncLayer(Generic[_In_co, _Out]):
    """Async twin of :class:`Layer`. Same variance, same rules."""

    _f: Callable[[Context[_In_co]], AbstractAsyncContextManager[Context[_Out]]]

    @classmethod
    def lift(cls, layer: Layer[_A, _B]) -> AsyncLayer[_A, _B]:
        """Adapt a sync layer so it composes into an async chain."""

        @asynccontextmanager
        async def _inner(ctx: Context[_A]) -> AsyncIterator[Context[_B]]:
            with layer._f(ctx) as out:
                yield out

        return AsyncLayer(_inner)

    def then(self: AsyncLayer[_A, _B], other: AsyncLayer[_B, _C]) -> AsyncLayer[_A, _B | _C]:
        """Build ``self``, then ``other`` with ``self``'s outputs available."""

        @asynccontextmanager
        async def _inner(ctx: Context[_A]) -> AsyncIterator[Context[_B | _C]]:
            async with AsyncExitStack() as stack:
                a_out = await stack.enter_async_context(self._f(ctx))
                b_out = await stack.enter_async_context(other._f(ctx.join(a_out)))
                yield a_out.join(b_out)

        return AsyncLayer(_inner)

    def build(
        self: AsyncLayer[_A, _B], ctx: Context[_A] = Context()
    ) -> AbstractAsyncContextManager[Context[_B]]:
        """Enter the layer; the ``async with`` block receives the built context."""

        return self._f(ctx)


def alayer(
    t: Tag[_T],
) -> Callable[
    [Callable[_P, AsyncGenerator[Union[Tag[_In], _T], Any]]],
    Callable[_P, AsyncLayer[_In, _T]],
]:
    """Async :func:`layer`. Request tags with ``value = yield tag``
    (``yield from`` is not allowed in async generators)."""

    def decorate(
        f: Callable[_P, AsyncGenerator[Union[Tag[_In], _T], Any]],
    ) -> Callable[_P, AsyncLayer[_In, _T]]:
        @wraps(f)
        def factory(*args: _P.args, **kwargs: _P.kwargs) -> AsyncLayer[_In, _T]:
            @asynccontextmanager
            async def enter(ctx: Context[_In]) -> AsyncIterator[Context[_T]]:
                gen = f(*args, **kwargs)
                try:
                    item = await gen.__anext__()
                    while isinstance(item, Tag):
                        item = await gen.asend(ctx._get(item))
                except StopAsyncIteration:
                    raise RuntimeError(_NO_SERVICE) from None
                try:
                    yield Context.of(t, item)
                except BaseException as exc:
                    try:
                        await gen.athrow(exc)
                    except StopAsyncIteration:
                        return
                    raise RuntimeError(_TOO_MANY)
                else:
                    try:
                        await gen.__anext__()
                    except StopAsyncIteration:
                        return
                    raise RuntimeError(_TOO_MANY)

            return AsyncLayer(enter)

        return factory

    return decorate
