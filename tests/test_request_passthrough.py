import asyncio
import json
import logging

from OneBot12Adapter.Core import OneBot12Adapter, _ensure_request_id


def test_native_request_id_stringified():
    data = {"type": "request", "request_id": 123}
    _ensure_request_id(data)
    assert data["request_id"] == "123"


def test_flag_mapped_when_native_missing():
    data = {"type": "request", "flag": "flag_abc"}
    _ensure_request_id(data)
    assert data["request_id"] == "flag_abc"


def test_native_id_preferred_over_flag():
    data = {"type": "request", "request_id": "rid_1", "flag": "flag_abc"}
    _ensure_request_id(data)
    assert data["request_id"] == "rid_1"


def test_missing_id_not_synthesized():
    data = {"type": "request", "user_id": "u1"}
    _ensure_request_id(data)
    assert "request_id" not in data


def test_empty_native_id_falls_back_to_flag():
    data = {"type": "request", "request_id": "", "flag": "f1"}
    _ensure_request_id(data)
    assert data["request_id"] == "f1"


def _make_adapter() -> OneBot12Adapter:
    ad = OneBot12Adapter.__new__(OneBot12Adapter)
    ad._bot_ids = {}
    ad._accounts_data = {}
    ad._pending_connect_meta = set()
    ad.logger = logging.getLogger("ob12-test")
    return ad


def _patch_emit(monkeypatch, emitted: list):
    import ErisPulse.Core as core

    async def fake_emit(event):
        emitted.append(event)

    monkeypatch.setattr(core.adapter, "emit", fake_emit)


def test_handle_message_request_passthrough(monkeypatch):
    ad = _make_adapter()
    monkeypatch.setattr(type(ad), "accounts", property(lambda self: {"default": object()}))
    emitted = []
    _patch_emit(monkeypatch, emitted)

    raw = json.dumps(
        {
            "type": "request",
            "detail_type": "friend",
            "user_id": "u1",
            "flag": "flag_x",
        }
    )
    asyncio.run(ad._handle_message(raw, "default"))

    assert len(emitted) == 1
    event = emitted[0]
    assert event["type"] == "request"
    assert event["request_id"] == "flag_x"
    assert event["onebot12_raw_type"] == "request"
    # 原始事件保持原样，补齐的 request_id 不回写 raw
    assert "request_id" not in event["onebot12_raw"]
    assert event["onebot12_raw"]["flag"] == "flag_x"


def test_handle_message_message_event_untouched(monkeypatch):
    ad = _make_adapter()
    monkeypatch.setattr(type(ad), "accounts", property(lambda self: {"default": object()}))
    emitted = []
    _patch_emit(monkeypatch, emitted)

    raw = json.dumps(
        {
            "type": "message",
            "detail_type": "private",
            "message": [{"type": "text", "data": {"text": "hi"}}],
        }
    )
    asyncio.run(ad._handle_message(raw, "default"))

    assert len(emitted) == 1
    event = emitted[0]
    assert event["type"] == "message"
    assert "request_id" not in event
