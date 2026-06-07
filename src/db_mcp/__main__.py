import argparse
import sys

from .server import run


def main() -> None:
    p = argparse.ArgumentParser(prog="db-mcp",
                                description="Deutsche Bahn MCP server")
    p.add_argument("--transport", choices=("stdio", "sse", "streamable-http"),
                   default="stdio",
                   help="default stdio. 'sse' or 'streamable-http' bind a local HTTP server.")
    p.add_argument("--host", default="127.0.0.1",
                   help="bind address for sse / streamable-http")
    p.add_argument("--port", type=int, default=8765,
                   help="port for sse / streamable-http")
    args = p.parse_args()
    try:
        run(transport=args.transport, host=args.host, port=args.port)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
