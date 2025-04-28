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
