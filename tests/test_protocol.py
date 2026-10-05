import json

import pytest

from bridge.protocol import ProtocolError, Request, Response


def test_request_round_trip() -> None:
    request = Request("1", "get_session_info", {})
    assert Request.from_json(request.to_json()) == request


def test_response_round_trip() -> None:
    response = Response("1", result={"connected": True})
    assert Response.from_json(response.to_json()) == response


def test_request_rejects_wrong_version() -> None:
    with pytest.raises(ProtocolError, match="Unsupported protocol version"):
        Request.from_json(json.dumps({"version": "0.1", "request_id": "1", "method": "x"}))


def test_response_requires_exactly_one_payload() -> None:
    response = Response("1", result={"ok": True}, error={"message": "bad"})
    with pytest.raises(ProtocolError, match="exactly one"):
        response.to_json()
