"""DEALFLOW MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from dealflow.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-dealflow[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-dealflow[mcp]'")
        return 1
    app = FastMCP("dealflow")

    @app.tool()
    def dealflow_scan(target: str) -> str:
        """Model your sales pipeline as a YAML state machine and compute conversion rates, stage velocity, and weighted forecast straight from CRM exports.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
