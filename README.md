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
ctx = context.from_dict({port_tag: 8080, host_tag: "localhost"})

# Run the function with the context
url = ctx.run(build_url())
print(url)  # Output: http://localhost:8080
```

## Context Creation

The library offers multiple ways to create contexts:

```python
# Single dependency
ctx1 = context.of(port_tag)(8080)

# Joining contexts
ctx2 = ctx1.join(context.of(host_tag)("localhost"))

# From pairs (more efficient for multiple dependencies)
ctx3 = context.from_pairs(
    (port_tag, 8080),
    (host_tag, "localhost"),
)

# From dictionary
ctx4 = context.from_dict({port_tag: 8080, host_tag: "localhost"})
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

## Why Use Monadic Context?

- **Testability**: Easy to mock dependencies for testing
- **Composability**: Combine and transform context-aware functions
- **Type Safety**: Full type checking with mypy/pyright
- **Separation of Concerns**: Clean separation between business logic and dependency resolution
- **No Runtime Reflection**: Unlike some DI frameworks, no runtime reflection or complex containers
- **No Mypy Plugins**: No need to reconfigure your programming environment

## License

MIT
