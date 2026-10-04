# Monadic Context

[![PyPI version](https://img.shields.io/pypi/v/monadic-context.svg)](https://pypi.org/project/monadic-context/)
[![Python versions](https://img.shields.io/pypi/pyversions/monadic-context.svg)](https://pypi.org/project/monadic-context/)
[![License](https://img.shields.io/github/license/sphaugh/python-monadic-context)](https://github.com/sphaugh/python-monadic-context/blob/main/LICENSE)

A lightweight, type-safe dependency injection library for Python.

## Features

- **Type-safe dependency injection** with full Python type hints support
- **Zero runtime dependencies** - just pure Python
- **Monadic interface** for composition and transformation
- **Pythonic generator-based syntax** for requesting dependencies
- **Flexible context creation** with multiple builder patterns

## Installation

Requires Python 3.9+

```bash
pip install monadic-context
```

Or with Poetry:

```bash
poetry add monadic-context
```

## Quick Example

```python
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
```

## Context Creation

The library offers multiple ways to create contexts:

```python
# Single dependency
ctx1 = context.of(port_tag, 8080)

# Adding a dependency
ctx2 = ctx1.extend(host_tag, "localhost")

# From pairs (each service is type-checked against its tag)
ctx3 = context.from_pairs(
    (port_tag, 8080),
    (host_tag, "localhost"),
)
```

## Advanced Usage

### Monadic Operations

The library supports standard monadic operations:

```python
# Map over a context-requiring function
home_url = context.pipe(build_url(), context.map(lambda url: f"{url}/home"))

result = ctx.run(home_url)
print(result)  # Output: http://localhost:8080/home
```

### With Service

For functions that take a service as first argument:

```python
import socket

db_conn_tag = context.Tag[socket.SocketType]("db_conn")


@context.with_service(db_conn_tag)
def configure_server(db_conn: socket.SocketType, timeout=30):
    # Use db_conn to configure server
    return {"connection": db_conn, "timeout": timeout}
```

## Layers

A layer is a recipe for building part of a context, with resource lifecycle.
Write one as a generator function: yield tags to request dependencies, then
yield the service once. Code after that yield is cleanup, exactly like
`contextlib.contextmanager`. The decorated function keeps its parameters and
returns a `Layer` when called.

```python
import sqlite3

import monadic_context as context
from monadic_context import Layer, layer, use

dsn_tag = context.Tag[str]("dsn")
db_tag = context.Tag[sqlite3.Connection]("db")


@layer(db_tag)
def open_db(timeout: float = 5.0):
    dsn = yield from use(dsn_tag)
    conn = sqlite3.connect(dsn, timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()


app = Layer.of(dsn_tag, ":memory:").then(open_db(timeout=1.0))

with app.build() as ctx:
    ctx.run(context.ask(db_tag)).execute("select 1")
# the connection is closed here; resources are released in reverse order
```

Chain layers with `then`; each step sees everything built before it, and the
type checker rejects a step whose requirements are not yet provided. Pyright
infers `open_db(...)` as `Layer[str, sqlite3.Connection]` from the tags it uses.

`@alayer(tag)` does the same for async generators (request with
`value = yield tag`, since `yield from` is not allowed there), and
`AsyncLayer.lift(sync_layer)` mixes a sync layer into an async chain.

The output type of a `Layer` is invariant, so `Layer[Never, A | B]` is not
assignable to `Layer[Never, A]`. This is what lets the checker infer chains
exactly.

## Why Use Monadic Context?

- **Testability**: Easy to mock dependencies for testing
- **Composability**: Combine and transform context-aware functions
- **Type Safety**: Full type checking with mypy/pyright
- **Separation of Concerns**: Clean separation between business logic and dependency resolution
- **No Runtime Reflection**: Unlike some DI frameworks, no runtime reflection or complex containers
- **No Mypy Plugins**: No need to reconfigure your programming environment

## License

MIT
