"""OneBot12 Request DSL 账户回退：未显式 Using 时回退 request_context 账户"""
import asyncio

from OneBot12Adapter.Core import OneBot12Adapter


def _make_request(account_id=None):
    ad = OneBot12Adapter.__new__(OneBot12Adapter)
    req = OneBot12Adapter.Request(ad, request_id="flag_1", account_id=account_id)
    return ad, req


def _patch(monkeypatch, req, captured):
    async def fake_call_api(endpoint, _account_id=None, **params):
        captured["account_id"] = _account_id
        return {"status": "ok"}

    monkeypatch.setattr(req._adapter, "call_api", fake_call_api)
    # 模拟事件分发链路注入的触发账户（request_context 兜底语义）
    monkeypatch.setattr(
        type(req),
        "request_context",
        property(lambda s: {"request_id": s._request_id, "account_id": "event_acc"}),
    )


def test_request_falls_back_to_request_context(monkeypatch):
    ad, req = _make_request()
    captured = {}
    _patch(monkeypatch, req, captured)

    asyncio.run(req._do_action(approve=True))
    assert captured["account_id"] == "event_acc"


def test_request_using_wins_over_context(monkeypatch):
    ad, req = _make_request(account_id="using_acc")
    captured = {}
    _patch(monkeypatch, req, captured)

    asyncio.run(req._do_action(approve=True))
    assert captured["account_id"] == "using_acc"
