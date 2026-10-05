"""In-FreeCAD local bridge service.

This module is deliberately importable outside FreeCAD so protocol tests and
packaging tools can inspect it without requiring a FreeCAD installation.
"""

from __future__ import annotations

import os
import socket
import threading
from typing import Any, Callable

try:
    from bridge.protocol import ProtocolError, Request, Response
except ImportError:
    from protocol import ProtocolError, Request, Response

DEFAULT_SOCKET_PATH = "/tmp/freecad-mcp.sock"


class BridgeService:
    def __init__(
        self,
        socket_path: str | None = None,
        session_provider: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.socket_path = socket_path or os.environ.get("FREECAD_MCP_SOCKET", DEFAULT_SOCKET_PATH)
        self.session_provider = session_provider or get_freecad_session_info
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._server is not None:
            raise RuntimeError("Bridge service is already running.")
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.socket_path)
        os.chmod(self.socket_path, 0o600)
        server.listen(8)
        server.settimeout(0.5)
        self._server = server
        self._thread = threading.Thread(target=self._serve, name="freecad-mcp-bridge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._server is not None:
            self._server.close()
            self._server = None
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass

    def _serve(self) -> None:
        assert self._server is not None
        while not self._stop.is_set():
            try:
                connection, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                self._handle(connection)

    def _handle(self, connection: socket.socket) -> None:
        request_id = "unknown"
        try:
            line = _read_line(connection)
            request = Request.from_json(line)
            request_id = request.request_id
            handlers = {
                "get_session_info": lambda: self.session_provider(),
                "list_documents": self._list_documents,
                "get_document_tree": lambda: self._get_document_tree(request.params),
                "get_object": lambda: self._get_object(request.params),
            }
            handler = handlers.get(request.method)
            if handler is not None:
                response = Response(request.request_id, result=handler())
            else:
                response = Response(
                    request.request_id,
                    error={
                        "code": "METHOD_NOT_FOUND",
                        "message": f"Unsupported bridge method: {request.method}",
                        "retryable": False,
                    },
                )
        except (ProtocolError, UnicodeDecodeError) as exc:
            response = Response(
                request_id,
                error={"code": "INVALID_REQUEST", "message": str(exc), "retryable": False},
            )
        except Exception as exc:
            response = Response(
                request_id,
                error={"code": "BRIDGE_ERROR", "message": str(exc), "retryable": False},
            )
        connection.sendall((response.to_json() + "\n").encode("utf-8"))

    @staticmethod
    def _list_documents() -> dict[str, Any]:
        return {"documents": list_freecad_documents()}

    @staticmethod
    def _get_document_tree(params: dict[str, Any]) -> dict[str, Any]:
        return {"document": get_freecad_document_tree(params)}

    @staticmethod
    def _get_object(params: dict[str, Any]) -> dict[str, Any]:
        return {"object": get_freecad_object(params)}


def _read_line(connection: socket.socket) -> str:
    data = bytearray()
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
        if b"\n" in chunk:
            break
    if not data:
        raise ProtocolError("Request was empty.")
    return bytes(data).split(b"\n", 1)[0].decode("utf-8")


def get_freecad_session_info() -> dict[str, Any]:
    try:
        import FreeCAD
    except ImportError as exc:
        raise RuntimeError("This session provider must run inside FreeCAD.") from exc

    active = FreeCAD.ActiveDocument
    return {
        "freecad_version": getattr(FreeCAD, "Version", lambda: "unknown")(),
        "active_document": (
            {
                "name": active.Name,
                "label": active.Label,
                "modified": _document_modified(active),
            }
            if active is not None
            else None
        ),
        "workbench": "unknown",
        "connected": True,
    }


def _freecad():
    try:
        import FreeCAD
    except ImportError as exc:
        raise RuntimeError("This operation must run inside FreeCAD.") from exc
    return FreeCAD


def list_freecad_documents() -> list[dict[str, Any]]:
    freecad = _freecad()
    return [
        {
            "name": document.Name,
            "label": document.Label,
            "modified": _document_modified(document),
            "object_count": len(document.Objects),
        }
        for document in freecad.listDocuments().values()
    ]


def _find_document(params: dict[str, Any]):
    freecad = _freecad()
    name = params.get("document")
    if name == "active" or name is None:
        document = freecad.ActiveDocument
    else:
        document = freecad.getDocument(name)
    if document is None:
        raise ValueError(f"Document not found: {name}")
    return document


def _serialize_object(obj: Any, children: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    result = {
        "name": obj.Name,
        "label": obj.Label,
        "type_id": obj.TypeId,
        "visibility": bool(getattr(obj.ViewObject, "Visibility", False)),
    }
    if children is not None:
        result["children"] = children
    return result


def get_freecad_document_tree(params: dict[str, Any]) -> dict[str, Any]:
    document = _find_document(params)
    max_depth = params.get("max_depth", 8)
    if not isinstance(max_depth, int) or max_depth < 0 or max_depth > 32:
        raise ValueError("max_depth must be an integer between 0 and 32.")

    def tree(obj: Any, depth: int) -> dict[str, Any]:
        children = []
        if depth < max_depth:
            children = [tree(child, depth + 1) for child in getattr(obj, "Group", [])]
        return _serialize_object(obj, children)

    roots = [tree(obj, 0) for obj in document.Objects if not getattr(obj, "Parents", [])]
    return {
        "name": document.Name,
        "label": document.Label,
        "modified": _document_modified(document),
        "objects": roots,
    }


def get_freecad_object(params: dict[str, Any]) -> dict[str, Any]:
    document = _find_document(params)
    object_name = params.get("object")
    if not isinstance(object_name, str) or not object_name:
        raise ValueError("object must be a non-empty string.")
    obj = document.getObject(object_name)
    if obj is None:
        raise ValueError(f"Object not found: {object_name}")
    return _serialize_object(obj)


def _document_modified(document: Any) -> bool:
    """Read the optional modified flag across supported FreeCAD versions."""
    return bool(getattr(document, "Modified", False))
