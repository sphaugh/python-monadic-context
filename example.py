from monadic_context import requires, use
import monadic_context as context

# Define tags for your dependencies
port_tag = context.Tag[int]("port")
host_tag = context.Tag[str]("host")


# Function that requires dependencies from context
@requires
def build_url():
    port = yield from use(port_tag)
    host = yield from use(host_tag)
    return f"http://{host}:{port}"


# Create a context with required dependencies
ctx = context.from_pairs((port_tag, 8080), (host_tag, "localhost"))

# Run the function with the context
url = ctx.run(build_url())
print(url)  # Output: http://localhost:8080

# Single dependency
ctx1 = context.of(port_tag, 8080)

# Joining contexts
ctx2 = ctx1.join(context.of(host_tag, "localhost"))

# From pairs (each service is type-checked against its tag)
ctx3 = context.from_pairs(
    (port_tag, 8080),
    (host_tag, "localhost"),
)


# Map over a context-requiring function
home_url = context.pipe(build_url(), context.map(lambda url: f"{url}/home"))

result = ctx.run(home_url)
print(result)  # Output: http://localhost:8080/home

import socket

db_conn_tag = context.Tag[socket.SocketType]("db_conn")


@context.with_service(db_conn_tag)
def configure_server(db_conn: socket.SocketType, timeout=30):
    # Use db_conn to configure server
    return {"connection": db_conn, "timeout": timeout}


# Layers: recipes for building a context, with resource lifecycle
import sqlite3

from monadic_context import Layer, layer

db_tag = context.Tag[sqlite3.Connection]("db")
row_count_tag = context.Tag[int]("row_count")


@layer(db_tag)
def open_db(host: str):  # normal parameters are kept; open_db("x") returns the Layer
    port = yield from use(
        port_tag
    )  # request a dependency; inferred Layer[int, Connection]
    conn = sqlite3.connect(f"file:{host}_{port}?mode=memory", uri=True)
    try:
        yield conn  # the first non-Tag yield is the service
    finally:
        conn.close()  # cleanup runs when the with block exits


@layer(row_count_tag)
def seed():
    # Layers downstream in a chain see everything built upstream
    conn = yield from use(db_tag)
    host = yield from use(host_tag)
    conn.execute("create table hosts (name text)")
    conn.execute("insert into hosts values (?)", (host,))
    yield conn.execute("select count(*) from hosts").fetchone()[0]


app = (
    Layer.of(port_tag, 8080)
    .then(Layer.of(host_tag, "localhost"))
    .then(open_db("localhost"))
    .then(seed())
)

with app.build() as ctx:
    print(ctx.run(context.ask(row_count_tag)))  # Output: 1
# The connection is closed here; resources are released in reverse order

# A layer can also read from a context passed to build()
with open_db("localhost").build(ctx1) as ctx:
    print(ctx.run(context.ask(db_tag)).execute("select 1").fetchone())  # Output: (1,)

# Async layers mirror the sync API; lift() mixes a sync layer into an async chain.
# Async generators cannot `yield from`, so request dependencies with `value = yield tag`.
import asyncio

from monadic_context import AsyncLayer, alayer

session_tag = context.Tag[str]("session")


@alayer(session_tag)
async def open_session():
    host = yield host_tag
    yield f"session for {host}"


async_app = AsyncLayer.lift(Layer.of(host_tag, "localhost")).then(open_session())


async def main():
    async with async_app.build() as ctx:
        print(ctx.run(context.ask(session_tag)))  # Output: session for localhost


asyncio.run(main())
