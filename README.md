# FreeCAD MCP Bridge

This project provides a local bridge that lets an MCP client such as Copilot inspect and, eventually, modify a FreeCAD document safely.

## Current status

The first milestone provides:

- A versioned newline-delimited JSON protocol.
- A local Unix-socket client/server transport.
- A FreeCAD-side service skeleton with `get_session_info`.
- An MCP adapter exposing session and read-only inspection tools over stdio.
- Document listing, object-tree inspection, and object metadata.
- A native add-on copy layout in `freecad_addon/`.

The adapter only connects to a bridge explicitly started by the FreeCAD add-on. It does not expose arbitrary Python execution.

## Read-only MCP tools

- `get_session_info`
- `list_documents`
- `get_document_tree`
- `get_object`

## Development

```bash
python -m pip install -e '.[test]'
pytest
```

Start the MCP adapter after starting the bridge from FreeCAD:

```bash
freecad-mcp-adapter
```

Set `FREECAD_MCP_SOCKET` to use a socket path other than the default `/tmp/freecad-mcp.sock`.

## FreeCAD add-on installation

The `freecad_addon/` directory is intended to be copied into FreeCAD's `Mod/FreeCADMCPBridge/` directory. The add-on currently exposes a small service API; GUI command registration will be added after the transport handshake is validated.
