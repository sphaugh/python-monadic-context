# pyright: reportUnnecessaryTypeIgnoreComment=true
"""Static inference checks for Context constructors. Checked by pyright in CI; never executed."""

from typing import assert_type

from monadic_context import Context, Tag, asks, from_pairs, of, with_service

port_tag = Tag[int]("port")
host_tag = Tag[str]("host")
flag_tag = Tag[bool]("flag")

assert_type(of(port_tag, 8080), Context[int])
assert_type(Context.of(port_tag, 8080), Context[int])
of(port_tag, "oops")  # pyright: ignore[reportArgumentType]

assert_type(from_pairs((port_tag, 8080)), Context[int])
assert_type(from_pairs((port_tag, 8080), (host_tag, "x")), Context[int | str])
assert_type(
    from_pairs((port_tag, 8080), (host_tag, "x"), (flag_tag, True)),
    Context[int | str | bool],
)
from_pairs((port_tag, 8080), (host_tag, 2.0))  # pyright: ignore[reportArgumentType]

ctx = of(port_tag, 8080)
assert_type(ctx.extend(host_tag, "x"), Context[int | str])
ctx.extend(host_tag, 2.0)  # pyright: ignore[reportArgumentType]

# Curried operators pin the tag's type before the function is checked.
asks(port_tag)(lambda n: n + 1)
asks(port_tag)(lambda s: s.upper())  # pyright: ignore[reportAttributeAccessIssue]


def greet(name: str) -> str:
    return name


with_service(port_tag)(greet)  # pyright: ignore[reportArgumentType]
