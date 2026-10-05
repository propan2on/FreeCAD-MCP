"""MCP stdio adapter for the FreeCAD bridge."""

from __future__ import annotations

from bridge.client import BridgeClient


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "This adapter requires MCP SDK 1.x. Install the project with `pip install -e .`."
        ) from exc

    server = FastMCP("FreeCAD")
    client = BridgeClient()

    @server.tool()
    def get_session_info() -> dict:
        """Return FreeCAD version, active document, workbench, and connection status."""
        return client.call("get_session_info")

    @server.tool()
    def list_documents() -> dict:
        """List open FreeCAD documents and their object counts."""
        return client.call("list_documents")

    @server.tool()
    def get_document_tree(document: str = "active", max_depth: int = 8) -> dict:
        """Return the read-only object tree for a FreeCAD document."""
        return client.call("get_document_tree", {"document": document, "max_depth": max_depth})

    @server.tool()
    def get_object(object: str, document: str = "active") -> dict:
        """Return metadata for one FreeCAD object by internal name."""
        return client.call("get_object", {"document": document, "object": object})

    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
