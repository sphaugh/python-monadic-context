from context.context import requires, use
import context.context as context
from context.tag import Tag


port_tag = Tag[int]("port")
host_tag = Tag[str]("host")


@requires
def build_url():
    port = yield from use(port_tag)
    host = yield from use(host_tag)
    return f"http://{host}:{port}"


def main():
    # Several ways to create contexts:
    basic = context.of(port_tag, 8080)

    # 1. Using multiple join operations
    context1 = context.of(port_tag, 8080).join(context.of(host_tag, "localhost"))

    # 2. Using from_pairs (more efficient for multiple services)
    context2 = context.from_pairs(
        (port_tag, 8080),
        (host_tag, "localhost"),
    )

    # 3. Using from_dict (more efficient for multiple services)
    context3 = context.from_dict({port_tag: 8080, host_tag: "localhost"})

    # All approaches produce equivalent contexts
    url = build_url()
    result = context3.run(url)
    print(result)  # Output: http://localhost:8080


if __name__ == "__main__":
    main()
