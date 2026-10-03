import asyncio

import pytest

from monadic_context import AsyncLayer, Layer, Tag, alayer, ask, layer, use
from monadic_context import of as context_of

a_tag = Tag[str]("a")
b_tag = Tag[str]("b")
cfg_tag = Tag[int]("cfg")
obj_tag = Tag[object]("obj")


def recorder(tag, name, events, fail_on=None):
    """A layer providing ``name`` under ``tag`` that logs enter/exit to ``events``."""

    @layer(tag)
    def _layer():
        if fail_on == "enter":
            raise RuntimeError(f"{name} failed to enter")
        events.append(f"enter {name}")
        try:
            yield name
        finally:
            events.append(f"exit {name}")
            if fail_on == "exit":
                raise RuntimeError(f"{name} failed to exit")

    return _layer()


def arecorder(tag, name, events, fail_on=None):
    @alayer(tag)
    async def _layer():
        if fail_on == "enter":
            raise RuntimeError(f"{name} failed to enter")
        events.append(f"enter {name}")
        try:
            yield name
        finally:
            events.append(f"exit {name}")
            if fail_on == "exit":
                raise RuntimeError(f"{name} failed to exit")

    return _layer()


# --- sync -------------------------------------------------------------------


def test_of_provides_value():
    with Layer.of(a_tag, "x").build() as ctx:
        assert ctx.run(ask(a_tag)) == "x"


def test_layer_requests_dependencies_with_use():
    @layer(a_tag)
    def dependent():
        n = yield from use(cfg_tag)
        yield "a" * n

    with Layer.of(cfg_tag, 3).then(dependent()).build() as ctx:
        assert ctx.run(ask(a_tag)) == "aaa"


def test_layer_requests_dependencies_with_bare_yield():
    @layer(a_tag)
    def dependent():
        n = yield cfg_tag
        yield "a" * n

    with Layer.of(cfg_tag, 2).then(dependent()).build() as ctx:
        assert ctx.run(ask(a_tag)) == "aa"


def test_then_builds_in_order_and_tears_down_in_reverse():
    events = []
    chain = recorder(a_tag, "a", events).then(recorder(b_tag, "b", events))

    with chain.build() as ctx:
        assert events == ["enter a", "enter b"]
        assert ctx.run(ask(a_tag)) == "a"
        assert ctx.run(ask(b_tag)) == "b"

    assert events == ["enter a", "enter b", "exit b", "exit a"]


def test_failure_entering_downstream_unwinds_upstream():
    events = []
    chain = recorder(a_tag, "a", events).then(recorder(b_tag, "b", events, fail_on="enter"))

    with pytest.raises(RuntimeError, match="b failed to enter"):
        with chain.build():
            pass

    assert events == ["enter a", "exit a"]


def test_failure_exiting_downstream_still_exits_upstream():
    events = []
    chain = recorder(a_tag, "a", events).then(recorder(b_tag, "b", events, fail_on="exit"))

    with pytest.raises(RuntimeError, match="b failed to exit"):
        with chain.build():
            pass

    assert events == ["enter a", "enter b", "exit b", "exit a"]


def test_body_exception_runs_cleanup_and_propagates():
    events = []

    with pytest.raises(ValueError, match="boom"):
        with recorder(a_tag, "a", events).build():
            raise ValueError("boom")

    assert events == ["enter a", "exit a"]


def test_layer_may_suppress_body_exception_like_contextmanager():
    @layer(a_tag)
    def swallowing():
        try:
            yield "a"
        except ValueError:
            pass

    with swallowing().build():
        raise ValueError("swallowed")


def test_code_after_service_yield_runs_on_normal_exit():
    events = []

    @layer(a_tag)
    def tail():
        yield "a"
        events.append("after yield")

    with tail().build():
        pass

    assert events == ["after yield"]


def test_same_layer_builds_independent_resources():
    @layer(obj_tag)
    def fresh():
        yield object()

    with fresh().build() as c1, fresh().build() as c2:
        assert c1.run(ask(obj_tag)) is not c2.run(ask(obj_tag))


def test_later_layer_wins_on_tag_collision():
    with Layer.of(a_tag, "first").then(Layer.of(a_tag, "second")).build() as ctx:
        assert ctx.run(ask(a_tag)) == "second"


def test_build_with_input_context_exposes_inputs():
    @layer(a_tag)
    def dependent():
        n = yield from use(cfg_tag)
        yield "a" * n

    with dependent().build(context_of(cfg_tag)(3)) as ctx:
        assert ctx.run(ask(a_tag)) == "aaa"


def test_missing_input_raises_keyerror_and_unwinds():
    events = []

    @layer(b_tag)
    def dependent():
        yield (yield from use(cfg_tag))

    chain = recorder(a_tag, "a", events).then(dependent())

    with pytest.raises(KeyError, match="'cfg' not found.*'a'"):
        with chain.build():
            pass

    assert events == ["enter a", "exit a"]


def test_layer_without_service_yield_raises_runtimeerror():
    @layer(a_tag)
    def none():
        return
        yield

    with pytest.raises(RuntimeError, match="did not yield a service"):
        with none().build():
            pass


def test_layer_yielding_twice_raises_runtimeerror():
    @layer(a_tag)
    def twice():
        yield "a"
        yield "b"

    with pytest.raises(RuntimeError, match="yielded again"):
        with twice().build():
            pass


def test_layer_factory_takes_parameters():
    @layer(a_tag)
    def greet(name: str, punct: str = "!"):
        n = yield from use(cfg_tag)
        yield f"hi {name}{punct}" * n

    with Layer.of(cfg_tag, 2).then(greet("bob", punct="?")).build() as ctx:
        assert ctx.run(ask(a_tag)) == "hi bob?hi bob?"


def test_async_layer_factory_takes_parameters():
    @alayer(a_tag)
    async def greet(name: str):
        yield f"hi {name}"

    async def main():
        async with greet("bob").build() as ctx:
            return ctx.run(ask(a_tag))

    assert asyncio.run(main()) == "hi bob"


# --- async ------------------------------------------------------------------


def run(coro):
    return asyncio.run(coro)


def test_async_lift_and_then_order():
    events = []
    chain = AsyncLayer.lift(recorder(a_tag, "a", events)).then(arecorder(b_tag, "b", events))

    async def main():
        async with chain.build() as ctx:
            assert events == ["enter a", "enter b"]
            return ctx.run(ask(a_tag)), ctx.run(ask(b_tag))

    assert run(main()) == ("a", "b")
    assert events == ["enter a", "enter b", "exit b", "exit a"]


def test_async_layer_requests_dependencies_with_bare_yield():
    @alayer(a_tag)
    async def dependent():
        n = yield cfg_tag
        yield "a" * n

    async def main():
        async with AsyncLayer.lift(Layer.of(cfg_tag, 3)).then(dependent()).build() as ctx:
            return ctx.run(ask(a_tag))

    assert run(main()) == "aaa"


def test_async_failure_entering_downstream_unwinds_lifted_upstream():
    events = []
    chain = AsyncLayer.lift(recorder(a_tag, "a", events)).then(
        arecorder(b_tag, "b", events, fail_on="enter")
    )

    async def main():
        async with chain.build():
            pass

    with pytest.raises(RuntimeError, match="b failed to enter"):
        run(main())
    assert events == ["enter a", "exit a"]


def test_async_failure_exiting_downstream_still_exits_upstream():
    events = []
    chain = arecorder(a_tag, "a", events).then(arecorder(b_tag, "b", events, fail_on="exit"))

    async def main():
        async with chain.build():
            pass

    with pytest.raises(RuntimeError, match="b failed to exit"):
        run(main())
    assert events == ["enter a", "enter b", "exit b", "exit a"]


def test_async_body_exception_runs_cleanup_and_propagates():
    events = []

    async def main():
        async with arecorder(a_tag, "a", events).build():
            raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run(main())
    assert events == ["enter a", "exit a"]


def test_async_missing_input_raises_keyerror():
    @alayer(a_tag)
    async def dependent():
        yield (yield cfg_tag)

    async def main():
        async with dependent().build():
            pass

    with pytest.raises(KeyError, match="'cfg' not found"):
        run(main())
