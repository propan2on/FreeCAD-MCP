"""FreeCAD GUI entry point for the Copilot MCP bridge."""

from __future__ import annotations

try:
    from .service import BridgeService
except ImportError:
    from service import BridgeService

_service: BridgeService | None = None


def start_bridge(socket_path: str | None = None) -> BridgeService:
    global _service
    if _service is None:
        _service = BridgeService(socket_path)
        _service.start()
    return _service


def stop_bridge() -> None:
    global _service
    if _service is not None:
        _service.stop()
        _service = None
