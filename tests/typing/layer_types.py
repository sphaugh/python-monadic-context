# pyright: reportUnnecessaryTypeIgnoreComment=true
"""Static inference checks for layers.

Checked by pyright in CI; never executed. Each ``pyright: ignore`` marks a
line that MUST be an error. If pyright stops reporting it, the unnecessary
ignore comment becomes an error itself, so a lost check cannot pass silently.
"""

from typing import Never, assert_type

from monadic_context import AsyncLayer, Context, Layer, Tag, alayer, layer, use


class Cfg: ...


class Log: ...


class Db: ...


class Cache: ...


cfg_tag = Tag[Cfg]("cfg")
log_tag = Tag[Log]("log")
db_tag = Tag[Db]("db")
cache_tag = Tag[Cache]("cache")


# Input type is inferred from the tags a layer requests; none requested means Never.
@layer(log_tag)
def log():
    yield Log()


@layer(db_tag)
def db():
    cfg = yield from use(cfg_tag)
    assert_type(cfg, Cfg)
    yield Db()


@layer(cache_tag)
def cache():
    yield from use(cfg_tag)
    yield from use(db_tag)
    yield Cache()


@layer(cache_tag)
def needs_log():
    yield from use(log_tag)
    yield Cache()


cfg = Layer.of(cfg_tag, Cfg())
assert_type(cfg, Layer[Never, Cfg])
assert_type(Context.of(cfg_tag, Cfg()), Context[Cfg])

# A value that does not match the tag's type is rejected, not joined into it.
Layer.of(cfg_tag, Db())  # pyright: ignore[reportArgumentType]
Context.of(cfg_tag, Db())  # pyright: ignore[reportArgumentType]


# Factories keep their parameters.
@layer(log_tag)
def log_with(level: int, prefix: str = ""):
    yield Log()


assert_type(log_with(1, prefix="x"), Layer[Never, Log])
log_with("not an int")  # pyright: ignore[reportArgumentType]
assert_type(log(), Layer[Never, Log])
assert_type(db(), Layer[Cfg, Db])
assert_type(cache(), Layer[Cfg | Db, Cache])


# Yielding the wrong service type is rejected.
@layer(db_tag)  # pyright: ignore[reportArgumentType]
def wrong():
    yield Cache()


# Chain with a strict-subset step (log needs nothing, Cfg is already built).
chain = cfg.then(log()).then(db()).then(cache())
assert_type(chain, Layer[Never, Cfg | Log | Db | Cache])

with chain.build() as ctx:
    assert_type(ctx, Context[Cfg | Log | Db | Cache])

with db().build(Context.of(cfg_tag, Cfg())) as ctx2:
    assert_type(ctx2, Context[Db])

# Nothing upstream provides Log: must be rejected at this step.
cfg.then(db()).then(needs_log())  # pyright: ignore[reportArgumentType]

# Output is invariant: narrowing by annotation is rejected (documented cost).
narrow: Layer[Never, Cfg] = cfg.then(db())  # pyright: ignore[reportAssignmentType]


# Async mirrors the sync rules. Requests are bare `yield tag` (no yield from in async generators).
@alayer(db_tag)
async def adb():
    yield cfg_tag
    yield Db()


assert_type(adb(), AsyncLayer[Cfg, Db])
achain = AsyncLayer.lift(cfg).then(adb())
assert_type(achain, AsyncLayer[Never, Cfg | Db])
AsyncLayer.lift(log()).then(adb())  # pyright: ignore[reportArgumentType]
