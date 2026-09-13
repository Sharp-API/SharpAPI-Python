"""Outgoing query keys for the odds endpoints, pinned against the server vocabulary.

``/odds`` and ``/odds/best`` accept the event filter under the canonical name
``event_id``. The spellings ``event``, ``events`` and ``event_ids`` are legacy
aliases (``sharp-api-go`` ``pkg/filters/parse.go``): an alias request still
returns rows, but the response carries ``Deprecation: true``, a ``Sunset`` date
that has already passed, and a ``Warning: 299`` header — and it is counted in
the server's ``sharpapi_go_filter_alias_usage`` migration metric.

The SDK used to send ``event``, so every SDK user was on the deprecated path.
These tests assert the wire key directly, because nothing else can: an alias
request succeeds, so a response-shape test cannot tell the two spellings apart.
The keyword argument is still called ``event`` — renaming it would break callers
— which is exactly why the wire key needs its own guard.
"""

import httpx
import pytest

from sharpapi import AsyncSharpAPI, SharpAPI

EVENT_IDS = ["evt_alpha", "evt_beta"]
EXPECTED_CSV = "evt_alpha,evt_beta"


def _record_into(seen: list[httpx.Request]):
    """A transport handler that records the request and returns an empty page."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"success": True, "data": []})

    return handler


def _sync_client(seen: list[httpx.Request]) -> SharpAPI:
    client = SharpAPI("sk_test")
    client._http = httpx.Client(
        base_url=client._http.base_url,
        transport=httpx.MockTransport(_record_into(seen)),
    )
    return client


def _async_client(seen: list[httpx.Request]) -> AsyncSharpAPI:
    client = AsyncSharpAPI("sk_test")
    client._http = httpx.AsyncClient(
        base_url=client._http.base_url,
        transport=httpx.MockTransport(_record_into(seen)),
    )
    return client


def _assert_canonical(request: httpx.Request, path_suffix: str) -> None:
    params = request.url.params
    assert request.url.path.endswith(path_suffix)
    assert params["event_id"] == EXPECTED_CSV
    # The deprecated alias must be absent, not merely accompanied by the
    # canonical name: sending both is still an alias request to the server.
    assert "event" not in params
    assert "events" not in params
    assert "event_ids" not in params


@pytest.mark.parametrize(
    ("method_name", "path_suffix"),
    [("get", "/odds"), ("best", "/odds/best")],
)
def test_sync_odds_sends_canonical_event_id(method_name, path_suffix):
    seen: list[httpx.Request] = []
    client = _sync_client(seen)
    try:
        getattr(client.odds, method_name)(event=EVENT_IDS)
    finally:
        client.close()

    assert len(seen) == 1
    _assert_canonical(seen[0], path_suffix)


@pytest.mark.parametrize(
    ("method_name", "path_suffix"),
    [("get", "/odds"), ("best", "/odds/best")],
)
async def test_async_odds_sends_canonical_event_id(method_name, path_suffix):
    seen: list[httpx.Request] = []
    client = _async_client(seen)
    try:
        await getattr(client.odds, method_name)(event=EVENT_IDS)
    finally:
        await client.close()

    assert len(seen) == 1
    _assert_canonical(seen[0], path_suffix)


def test_single_event_id_is_not_wrapped_in_a_list():
    """A scalar ``event`` reaches the wire unchanged, under the canonical key."""
    seen: list[httpx.Request] = []
    client = _sync_client(seen)
    try:
        client.odds.get(event="evt_alpha")
    finally:
        client.close()

    assert seen[0].url.params["event_id"] == "evt_alpha"
    assert "event" not in seen[0].url.params


def test_omitting_the_event_filter_sends_neither_spelling():
    """``None`` is dropped, so an unfiltered call carries no event key at all."""
    seen: list[httpx.Request] = []
    client = _sync_client(seen)
    try:
        client.odds.get(sport="baseball")
    finally:
        client.close()

    params = seen[0].url.params
    assert params["sport"] == "baseball"
    assert "event_id" not in params
    assert "event" not in params
