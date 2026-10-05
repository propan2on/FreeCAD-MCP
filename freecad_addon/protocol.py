"""Bundled protocol copy for native FreeCAD Mod installation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

PROTOCOL_VERSION = "1.0"


class ProtocolError(ValueError):
    """Raised when a bridge message does not match the wire contract."""


@dataclass(frozen=True)
class Request:
    request_id: str
    method: str
    params: dict[str, Any]

    @classmethod
    def from_json(cls, value: str) -> "Request":
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ProtocolError("Message is not valid JSON.") from exc
        if not isinstance(payload, dict) or payload.get("version") != PROTOCOL_VERSION:
            raise ProtocolError("Invalid request envelope.")
        request_id = payload.get("request_id")
        method = payload.get("method")
        params = payload.get("params", {})
        if not isinstance(request_id, str) or not request_id:
            raise ProtocolError("request_id must be a non-empty string.")
        if not isinstance(method, str) or not method:
            raise ProtocolError("method must be a non-empty string.")
        if not isinstance(params, dict):
            raise ProtocolError("params must be an object.")
        return cls(request_id, method, params)


@dataclass(frozen=True)
class Response:
    request_id: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_json(self) -> str:
        if (self.result is None) == (self.error is None):
            raise ProtocolError("A response must contain exactly one of result or error.")
        payload = {"version": PROTOCOL_VERSION, "request_id": self.request_id}
        payload["result" if self.result is not None else "error"] = (
            self.result if self.result is not None else self.error
        )
        return json.dumps(payload, separators=(",", ":"))
