"""Outgoing query keys for the odds endpoints, pinned against the server vocabulary.

``/odds`` and ``/odds/best`` accept the event filter under the canonical name
``event_id``, and the live filter under ``is_live``. The spellings ``event``,
``events``, ``event_ids`` and ``live`` are legacy aliases (the server's own
filter parser is the source of that mapping): an alias request still returns
rows, but the response carries ``Deprecation: true`` and a ``Warning: 299``
header.

No ``Sunset`` date is advertised. One was (2026-07-01), it passed without any
alias being dropped, and the server stopped sending an expired date rather than
keep making a promise that had already broken. The current plan is
*migrate first, date later*: the SDK moves to the canonical names
now, and a real cutoff date is named only once outside use is low.

The SDK used to send both aliases, so every SDK user was on the deprecated
path. These tests assert the wire key directly, because nothing else can: an
alias request succeeds, so a response-shape test cannot tell the two spellings
apart. The keyword arguments are still called ``event`` and ``live`` — renaming
them would break callers — which is exactly why the wire keys need their own
guards.
"""

import inspect
from typing import Any

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


# ---------------------------------------------------------------------------
# The ``live`` filter, same shape as ``event`` above.
#
# ``live`` is the deprecated alias of ``is_live``. Both spellings are in
# ``_SERVER_ODDS_PARAMS`` below, because both are accepted — which is exactly
# why that list cannot be the guard here. Only a direct assertion on the wire
# key can tell the canonical spelling from the alias, since an alias request
# returns the same rows with the same status.
#
# The keyword argument stays ``live``. Renaming it would break every caller,
# for no gain the wire key does not already deliver.

# Discovered, not listed: every public method on every resource that accepts a
# ``live`` keyword. A method gaining the filter later is covered the day it is
# added rather than the day someone remembers this file — the same reasoning as
# ``test_every_odds_keyword_maps_to_a_key_the_server_accepts``.
def _methods_accepting_live(client: Any) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for resource_name in dir(client):
        if resource_name.startswith("_"):
            continue
        resource = getattr(client, resource_name)
        module = getattr(type(resource), "__module__", "")
        if not module.startswith("sharpapi."):
            continue
        for method_name in dir(resource):
            if method_name.startswith("_"):
                continue
            method = getattr(resource, method_name)
            if not callable(method):
                continue
            try:
                signature = inspect.signature(method)
            except (TypeError, ValueError):
                continue
            if "live" in signature.parameters:
                found.append((resource_name, method_name))
    return sorted(found)


# The discovery above would pass vacuously if it found nothing — a renamed
# resource attribute or a module move would silently empty the list. This is
# the positive control: the methods known to take the filter on 2026-10-05.
# A method legitimately added or removed changes this set deliberately.
_METHODS_ACCEPTING_LIVE = [
    ("arbitrage", "get"),
    ("ev", "get"),
    ("events", "list"),
    ("low_hold", "get"),
    ("middles", "get"),
    ("odds", "best"),
    ("odds", "get"),
]


def test_live_filter_discovery_finds_every_known_method():
    """Guards the guard: an empty or shrunken walk must fail, not pass quietly."""
    client = SharpAPI("sk_test")
    try:
        assert _methods_accepting_live(client) == _METHODS_ACCEPTING_LIVE
    finally:
        client.close()


@pytest.mark.parametrize(("resource_name", "method_name"), _METHODS_ACCEPTING_LIVE)
def test_sync_live_filter_is_sent_as_is_live(resource_name, method_name):
    seen: list[httpx.Request] = []
    client = _sync_client(seen)
    try:
        getattr(getattr(client, resource_name), method_name)(live=True)
    finally:
        client.close()

    assert len(seen) == 1
    params = seen[0].url.params
    assert params["is_live"] == "true"
    # Absent, not merely accompanied: sending both is still an alias request.
    assert "live" not in params


@pytest.mark.parametrize(("resource_name", "method_name"), _METHODS_ACCEPTING_LIVE)
async def test_async_live_filter_is_sent_as_is_live(resource_name, method_name):
    seen: list[httpx.Request] = []
    client = _async_client(seen)
    try:
        await getattr(getattr(client, resource_name), method_name)(live=True)
    finally:
        await client.close()

    assert len(seen) == 1
    params = seen[0].url.params
    assert params["is_live"] == "true"
    assert "live" not in params


def test_live_false_is_sent_and_not_dropped():
    """``False`` is a real filter value — prematch only — and must survive.

    The params dict drops ``None``, and a truthiness test instead of an
    is-None test would drop ``False`` with it, silently widening the query
    from prematch-only to everything. Pinned on both spellings.
    """
    seen: list[httpx.Request] = []
    client = _sync_client(seen)
    try:
        client.odds.get(live=False)
    finally:
        client.close()

    params = seen[0].url.params
    assert params["is_live"] == "false"
    assert "live" not in params


def test_omitting_the_live_filter_sends_neither_spelling():
    seen: list[httpx.Request] = []
    client = _sync_client(seen)
    try:
        client.odds.get(sport="baseball")
    finally:
        client.close()

    params = seen[0].url.params
    assert params["sport"] == "baseball"
    assert "is_live" not in params
    assert "live" not in params


# ---------------------------------------------------------------------------
# Every wire key the SDK can emit for ``/odds`` must be one the server accepts.
#
# The API answers 400 for a query key it does not recognise, and the 400 body
# lists the keys it does accept (``recognized_params``), for example:
#   GET /api/v1/odds?sport=baseball&limit=1&team=x
# ``per_page`` and ``bookmakers`` answer 200, which shows the check itself works.
_SERVER_ODDS_PARAMS = frozenset({
    "api_key", "book", "bookmakers", "books", "competition_id",
    "competition_ids", "cursor", "date", "date_range", "devig_book", "event",
    "event_group", "event_id", "event_ids", "events", "group", "group_by",
    "include_fair_odds", "include_open", "include_total", "is_alternate_line",
    "is_impossible_scoreline", "is_live", "is_main_line", "is_player_prop",
    "is_stale_pregame_price", "league", "leagues", "limit", "live", "market",
    "market_segment", "market_segments", "market_type", "markets",
    "max_market_width", "max_odds", "max_odds_age", "max_opportunity_age",
    "min_ev", "min_kelly", "min_market_width", "min_odds", "min_profit",
    "offset", "per_page", "player_name", "q", "selection", "sharp_book",
    "season_type", "sort", "sport", "sports", "sportsbook", "sportsbooks", "sportsbooks[]",
    "state",
})

# One sample per keyword argument of ``odds.get``. Kept explicit rather than
# derived from annotations so that adding a keyword argument without deciding
# what it puts on the wire fails this file loudly — see the coverage assertion
# in ``test_every_odds_keyword_maps_to_a_key_the_server_accepts``.
_ODDS_KWARG_SAMPLES = {
    "sportsbook": "pinnacle",
    "sport": "baseball",
    "league": "mlb",
    "market": "moneyline",
    "event": "evt_alpha",
    "live": True,
    "sort": "-odds_american",
    "group_by": "event",
    "season_type": "Preseason",
    "limit": 1,
    "offset": 0,
}


def test_every_odds_keyword_maps_to_a_key_the_server_accepts():
    """No ``odds.get`` keyword may put a key on the wire that answers 400.

    This is the guard that ``fields`` needed and did not have. It is written
    against the *signature*, not a fixed list of keywords, so a keyword added
    later is covered the day it is added rather than the day someone remembers
    this file.
    """
    seen: list[httpx.Request] = []
    client = _sync_client(seen)
    signature = set(inspect.signature(client.odds.get).parameters)

    # Non-vacuity: a new keyword with no sample would otherwise go untested.
    assert signature == set(_ODDS_KWARG_SAMPLES), (
        "add the new odds.get keyword(s) to _ODDS_KWARG_SAMPLES: "
        f"{signature ^ set(_ODDS_KWARG_SAMPLES)}"
    )

    try:
        client.odds.get(**_ODDS_KWARG_SAMPLES)
    finally:
        client.close()

    sent = set(seen[0].url.params)
    # Every keyword actually reached the wire, so the check below has something
    # to bite on — a request that silently dropped its filters would pass a bare
    # subset assertion while testing nothing.
    assert len(sent) == len(_ODDS_KWARG_SAMPLES)

    rejected = sent - _SERVER_ODDS_PARAMS
    assert rejected == set(), (
        f"odds.get sends query key(s) the server answers 400 for: {sorted(rejected)}"
    )


@pytest.mark.parametrize("removed", ["fields", "team", "has_score", "add_sportsbook"])
def test_removed_odds_keywords_are_rejected_at_the_call_site(removed):
    """A caller gets a ``TypeError`` here, not a 400 from the server.

    ``fields`` was a documented keyword argument that the API rejects; ``team``,
    ``has_score``, and ``add_sportsbook`` are parameters the API has never
    supported and must not reappear. Failing in the SDK names the problem at the
    call site.
    """
    seen: list[httpx.Request] = []
    client = _sync_client(seen)
    # Annotated `Any` deliberately: pyright resolves `**` unpacking against the
    # signature, so a `dict[str, str]` literal here is reported as a type error on
    # `live`/`limit`/`offset` and the call never reaches runtime. The whole point of
    # this test is what happens at RUNTIME for a keyword that no longer exists, so
    # the value type has to stay opaque to the checker.
    kwargs: dict[str, Any] = {removed: "x"}
    try:
        with pytest.raises(TypeError):
            client.odds.get(**kwargs)
    finally:
        client.close()

    assert seen == []
