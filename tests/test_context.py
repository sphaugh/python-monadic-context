from hypothesis import given
from hypothesis import strategies as st

from context.context import (
    ask,
    asks,
    of,
    map,
    bind,
    pure,
    apply,
    then,
    traverse,
    with_service,
    from_dict,
    from_pairs,
    requires,
    use,
    Tag,
)
from context.pipe import compose, pipe


def _double(x: int) -> int:
    return x * 2


def _increment(x: int) -> int:
    return x + 1


double = st.functions(like=_double, returns=st.integers(), pure=True)

increment = st.functions(like=_increment, returns=st.integers(), pure=True)


def make_test_context(value):
    tag = Tag[int]("test")
    return of(tag)(value), tag


@given(st.integers())
def test_map_identity_law(value):
    context, tag = make_test_context(value)

    ma = ask(tag)
    mb = map(lambda x: x)(ma)

    assert context.run(ma) == context.run(mb)


@given(st.integers(), double, increment)
def test_map_composition_law(value, f, g):
    context, tag = make_test_context(value)

    ma = ask(tag)
    left = map(compose(f, g))
    right = compose(map(f), map(g))

    assert context.run(left(ma)) == context.run(right(ma))


@given(st.integers())
def test_bind_left_identity(value):
    context, tag = make_test_context(value)

    @with_service(tag)
    def action(a: int, b: int):
        return a + b

    left = pipe(pure(value), bind(action))
    right = action(value)

    assert context.run(left) == context.run(right)


@given(st.integers())
def test_bind_right_identity(value):
    context, tag = make_test_context(value)

    ma = ask(tag)

    left = pipe(ma, bind(pure))
    right = ma

    assert context.run(left) == context.run(right)


@given(st.integers())
def test_bind_associativity(value):
    context, tag = make_test_context(value)

    ma = ask(tag)

    @with_service(tag)
    def f(_: int, a: int):
        return a * 2

    @with_service(tag)
    def g(_: int, a: int):
        return a + 3

    left = pipe(ma, bind(f), bind(g))
    right = pipe(ma, bind(lambda x: pipe(f(x), bind(g))))

    assert context.run(left) == context.run(right)


@given(st.integers(), double)
def test_apply(value, f):
    context, tag = make_test_context(value)

    mf = pure(f)
    ma = ask(tag)
    result = apply(ma)(mf)

    assert f(value) == context.run(result)


@given(st.integers())
def test_then(value):
    context, tag = make_test_context(value)

    ma = ask(tag)
    mb = pure(42)
    result = then(ma)(mb)

    assert context.run(result) == 42


@given(st.lists(st.integers(), min_size=1, max_size=10))
def test_traverse(values):
    first_value = values[0]
    context, tag = make_test_context(first_value)

    @with_service(tag)
    def transform(a: int, b: int):
        return a * b

    result = traverse(transform)(values)

    expected = [v * first_value for v in values]
    assert context.run(result) == expected


@given(st.integers())
def test_asks(value):
    context, tag = make_test_context(value)

    result = asks(tag)(lambda x: x + 1)

    assert context.run(result) == value + 1


@given(st.integers())
def test_with_service(value):
    context, tag = make_test_context(value)

    @with_service(tag)
    def increment_service(a: int, b: int):
        return a + b

    fn = increment_service(5)

    assert context.run(fn) == value + 5


def test_tag_creation_methods():
    tag1 = Tag[int]("tag1")
    tag2 = Tag[str].new("tag2")

    context = of(tag1)(42).extend(tag2, "hello")

    assert context.run(ask(tag1)) == 42
    assert context.run(ask(tag2)) == "hello"


def test_context_creation_methods():
    tag1 = Tag[int]("tag1")
    tag2 = Tag[str]("tag2")

    context1 = from_dict({tag1: 42, tag2: "hello"})
    assert context1.run(ask(tag1)) == 42
    assert context1.run(ask(tag2)) == "hello"

    context2 = from_pairs((tag1, 24), (tag2, "world"))
    assert context2.run(ask(tag1)) == 24
    assert context2.run(ask(tag2)) == "world"


def test_context_extension():
    tag1 = Tag[int]("tag1")
    tag2 = Tag[str]("tag2")
    tag3 = Tag[float]("tag3")

    context1 = of(tag1)(42)
    context2 = of(tag2)("hello")

    joined = context1.join(context2)
    assert joined.run(ask(tag1)) == 42
    assert joined.run(ask(tag2)) == "hello"

    extended = context1.extend(tag3, True)
    assert extended.run(ask(tag1)) == 42
    assert extended.run(ask(tag3)) is True


def test_requires_and_use():
    tag1 = Tag[int]("tag1")
    tag2 = Tag[str]("tag2")

    @requires
    def build_message():
        num = yield from use(tag1)
        msg = yield from use(tag2)
        return f"{msg} {num}"

    context = from_pairs((tag1, 42), (tag2, "The answer is"))

    result = context.run(build_message())

    assert result == "The answer is 42"
