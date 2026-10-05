"""Synchronous client for the local FreeCAD bridge service."""

from __future__ import annotations

import itertools
import os
import socket
from typing import Any

from .protocol import Request, Response

DEFAULT_SOCKET_PATH = "/tmp/freecad-mcp.sock"


class BridgeConnectionError(ConnectionError):
    """Raised when the FreeCAD bridge cannot be reached."""


class BridgeClient:
    def __init__(self, socket_path: str | None = None, timeout: float = 5.0) -> None:
        self.socket_path = socket_path or os.environ.get("FREECAD_MCP_SOCKET", DEFAULT_SOCKET_PATH)
        self.timeout = timeout
        self._request_ids = itertools.count(1)

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request = Request(str(next(self._request_ids)), method, params or {})
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(self.timeout)
                connection.connect(self.socket_path)
                connection.sendall((request.to_json() + "\n").encode("utf-8"))
                response_line = self._read_line(connection)
        except OSError as exc:
            raise BridgeConnectionError(
                f"Unable to connect to FreeCAD bridge at {self.socket_path}: {exc}"
            ) from exc
        response = Response.from_json(response_line)
        if response.request_id != request.request_id:
            raise BridgeConnectionError("FreeCAD bridge returned a mismatched request ID.")
        if response.error is not None:
            raise BridgeConnectionError(response.error.get("message", "FreeCAD bridge error."))
        assert response.result is not None
        return response.result

    @staticmethod
    def _read_line(connection: socket.socket) -> str:
        chunks: list[bytes] = []
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        if not chunks:
            raise BridgeConnectionError("FreeCAD bridge closed the connection without a response.")
        return b"".join(chunks).split(b"\n", 1)[0].decode("utf-8")
