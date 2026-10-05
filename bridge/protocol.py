"""Versioned newline-delimited JSON protocol used by both bridge processes."""

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

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": PROTOCOL_VERSION,
                "request_id": self.request_id,
                "method": self.method,
                "params": self.params,
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, value: str) -> "Request":
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ProtocolError("Message is not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ProtocolError("Message must be a JSON object.")
        if payload.get("version") != PROTOCOL_VERSION:
            raise ProtocolError("Unsupported protocol version.")
        request_id = payload.get("request_id")
        method = payload.get("method")
        params = payload.get("params", {})
        if not isinstance(request_id, str) or not request_id:
            raise ProtocolError("request_id must be a non-empty string.")
        if not isinstance(method, str) or not method:
            raise ProtocolError("method must be a non-empty string.")
        if not isinstance(params, dict):
            raise ProtocolError("params must be an object.")
        return cls(request_id=request_id, method=method, params=params)


@dataclass(frozen=True)
class Response:
    request_id: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_json(self) -> str:
        if (self.result is None) == (self.error is None):
            raise ProtocolError("A response must contain exactly one of result or error.")
        payload: dict[str, Any] = {
            "version": PROTOCOL_VERSION,
            "request_id": self.request_id,
        }
        if self.result is not None:
            payload["result"] = self.result
        else:
            payload["error"] = self.error
        return json.dumps(payload, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> "Response":
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ProtocolError("Message is not valid JSON.") from exc
        if not isinstance(payload, dict) or payload.get("version") != PROTOCOL_VERSION:
            raise ProtocolError("Invalid response envelope.")
        request_id = payload.get("request_id")
        result = payload.get("result")
        error = payload.get("error")
        if not isinstance(request_id, str) or not request_id:
            raise ProtocolError("request_id must be a non-empty string.")
        if (result is None) == (error is None):
            raise ProtocolError("A response must contain exactly one of result or error.")
        if result is not None and not isinstance(result, dict):
            raise ProtocolError("result must be an object.")
        if error is not None and not isinstance(error, dict):
            raise ProtocolError("error must be an object.")
        return cls(request_id=request_id, result=result, error=error)
