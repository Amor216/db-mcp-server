# db-mcp-server

An [MCP](https://modelcontextprotocol.io) server that exposes the Deutsche Bahn public transport API to any MCP-compatible client (Claude Desktop, Cursor, Cline, Continue, etc.). Six tools cover station search, departures, journey planning, trip details, station info, and nearby stations.

Built on the [v6.db.transport.rest](https://v6.db.transport.rest) API, which is free and requires no authentication. ~400 lines of Python.

## Tools

| Tool | Purpose |
|---|---|
| `search_station` | Find German train stations by name. Returns IDs needed by the other tools. |
| `get_departures` | Upcoming departures from a station with line, direction, platform, delay. |
| `plan_journey` | Connection between two stations with duration, transfers, platforms. |
| `get_trip_details` | Full stop-by-stop schedule for one specific train. |
| `get_station_info` | Address, coordinates, and facilities (lifts, accessible toilets, etc.) for a station. |
| `nearby_stations` | Stations near a lat/lon coordinate. |

## Install via uvx (no clone needed)

If your client supports it, you can run the server straight from this repo with no install step:

```json
{
  "mcpServers": {
    "deutsche-bahn": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Amor216/db-mcp-server", "db-mcp"]
    }
  }
}
```

## Claude Desktop setup

Put the snippet above into your `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Restart Claude Desktop. The tools appear under the hammer icon. Try asking:

> When is the next ICE from Berlin Hbf to Munich?

## Local development

```
git clone https://github.com/Amor216/db-mcp-server
cd db-mcp-server
uv sync
uv run pytest -q
```

To run the server against stdin/stdout directly:

```
uv run db-mcp
```

That's the same thing your MCP client will spawn under the hood.

## Layout

```
src/db_mcp/
  server.py        FastMCP server, 5 tools
  client.py        thin httpx wrapper around transport.rest
  formatters.py    API JSON -> compact text the LLM can read

tests/
  test_client.py     httpx mocked with respx
  test_formatters.py snapshot-style assertions
  test_server.py     tool-call smoke tests
```

## Why the formatter layer

The transport.rest API returns deeply nested JSON. Handing that straight to an LLM wastes context and confuses the model. The formatters turn each response into compact text, one departure or one journey per line, so the model reads it the way a human reads a station board.

## Rate limits

The upstream API allows 100 requests/minute (200 burst). The server makes one request per tool call, so a normal conversation stays well under the limit. There's no caching layer right now since the data (delays, platforms) is real-time and would lose value if stale.

## License

MIT.
