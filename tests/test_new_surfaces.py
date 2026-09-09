"""Contract guards for the /players, /prediction-markets, /settlements and
/parlay/price surfaces, and for the parlay error codes.

Fixture provenance
------------------
Unlike ``*_live.json`` in this directory, the ``*_contract.json`` fixtures
were NOT captured from a live call. They are transcribed from the server's
response structs on ``sharp-api-go`` ``main`` — ``players.go``
(``PlayerResult``), ``prediction_markets.go`` (``PMMarket`` / ``PMCategory``),
``pkg/settlements/settlements.go`` (``Settlement`` + the handler envelope) and
``endpoints_parlay.go`` (``parlayLegEcho`` / ``parlayModel``). None of those
types declares a ``MarshalJSON``, so the struct tags ARE the wire format.

Values are illustrative, not observed: no real sportsbook price, player, or
event appears here. What the fixtures pin is SHAPE — key names, which keys are
omitted when empty (``omitempty``) and which arrive as an explicit ``null``
(pointer fields without ``omitempty``: ``line``, ``bid``/``ask``/``last``,
``linked_event_id``, ``parlay.price``). Recapture from a live call when the
server contract intentionally changes.
"""

import json
from pathlib import Path

import pytest

from sharpapi._base import parse_response, parse_settlements_response
from sharpapi.models import (
    ParlayPrice,
    Player,
    PredictionMarket,
    PredictionMarketCategory,
    Settlement,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _payload(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _rows(name: str) -> list[dict]:
    rows = _payload(name).get("data") or []
    assert rows, f"{name} has no rows — an empty fixture asserts nothing"
    return rows


# --------------------------------------------------------------------------- #
# /players
# --------------------------------------------------------------------------- #


def test_players_response_parses():
    parsed = parse_response(_payload("players_contract.json"), Player)
    assert len(parsed.data) == 2
    first = parsed.data[0]
    assert first.id == "baseball_mlb_example_player"
    assert first.display_name == "Example Player"
    assert first.leagues == ["mlb"]
    assert first.team_id == "baseball_mlb_example_team"


def test_player_omitted_optionals_are_none_not_missing():
    """``first_name``/``last_name``/``team_id`` carry ``omitempty``: the wire
    drops the key entirely rather than sending null."""
    second = parse_response(_payload("players_contract.json"), Player).data[1]
    assert second.first_name is None
    assert second.last_name is None
    assert second.team_id is None
    assert second.leagues == []


# --------------------------------------------------------------------------- #
# /prediction-markets
# --------------------------------------------------------------------------- #


def test_prediction_markets_response_parses():
    parsed = parse_response(_payload("prediction_markets_contract.json"), PredictionMarket)
    assert len(parsed.data) == 2
    game_tied = parsed.data[0]
    assert game_tied.market_id == "kalshi:KXEXAMPLEGAME-26SEP09"
    assert game_tied.source_ids.market_id == "KXEXAMPLEGAME-26SEP09"
    assert game_tied.outcomes[0].price.american == -122
    assert game_tied.outcomes[0].price.probability == 0.55
    assert game_tied.sportsbook_ref is not None
    assert game_tied.sportsbook_ref.id == "kalshi"


def test_prediction_market_linked_event_id_is_null_on_futures():
    """``linked_event_id`` is sent WITHOUT omitempty and is always null for a
    futures / question contract — its per-book synthetic event id is not a
    stable join key and must never be offered as one."""
    parsed = parse_response(_payload("prediction_markets_contract.json"), PredictionMarket)
    assert parsed.data[0].linked_event_id == "baseball_mlb_example_event"
    assert parsed.data[1].linked_event_id is None


def test_prediction_market_absent_quotes_parse_as_none():
    """bid/ask/last arrive as explicit nulls when no quote is resting."""
    parsed = parse_response(_payload("prediction_markets_contract.json"), PredictionMarket)
    no_side = parsed.data[0].outcomes[1]
    assert (no_side.bid, no_side.ask, no_side.last) == (None, None, None)


def test_prediction_market_categories_parse():
    parsed = parse_response(
        _payload("prediction_market_categories_contract.json"), PredictionMarketCategory
    )
    sports = parsed.data[0]
    assert sports.id == "sports"
    assert sports.market_count == 412
    assert [b.id for b in sports.books] == ["kalshi", "polymarket"]
    assert sports.books[0].market_count == 260


# --------------------------------------------------------------------------- #
# /settlements — `data` is an OBJECT, not a list
# --------------------------------------------------------------------------- #


def test_settlements_page_parses():
    """``parse_response`` coerces ``data`` into a list, which would turn this
    page object into a one-element list of the wrong model — hence the
    dedicated parser."""
    parsed = parse_settlements_response(_payload("settlements_contract.json"))
    page = parsed.data
    assert parsed.success is True
    assert page.total_settlements == 2
    assert page.truncated is False
    assert page.next_offset is None
    assert len(page.settlements) == 2
    assert page.settlements[0].outcome == "won"
    assert page.settlements[0].line == 8.5
    assert page.settlements[1].outcome == "push"
    assert page.settlements[1].player_id == "baseball_mlb_example_player"
    assert page.settlements[1].hash_id is None


def test_settlements_meta_survives_parsing():
    """``grading_cutoff``/``limit``/``offset``/``updated_at`` were undeclared
    on ``ResponseMeta``; pydantic drops undeclared keys silently, so the whole
    settlements window read back as ``None``."""
    meta = parse_settlements_response(_payload("settlements_contract.json")).meta
    assert meta is not None
    assert meta.source == "ev_grading"
    assert meta.limit == 100
    assert meta.offset == 0
    assert meta.grading_cutoff == "2026-07-19"
    assert meta.updated_at == "2026-09-09T18:00:00.123456789Z"
    assert meta.filters == {
        "hash_id": None,
        "game_id": "baseball_mlb_example_event",
        "market_type": None,
        "selection": None,
        "player_id": None,
    }


# --------------------------------------------------------------------------- #
# /parlay/price
# --------------------------------------------------------------------------- #


def test_parlay_priced_response_parses():
    result = ParlayPrice.model_validate(_payload("parlay_price_contract.json")["data"])
    assert result.sportsbook == "example_book"
    assert len(result.legs) == 3
    assert result.legs[0].line is None
    assert result.legs[1].line == 8.5
    assert result.legs[1].market_segment == "full_game"
    assert result.legs[2].player_name == "Example Player"
    assert result.parlay.price is not None
    assert result.parlay.price.odds_american == 557
    assert result.parlay.leg_count == 3
    assert result.parlay.source == "sharpapi_model"
    assert result.warnings is None


def test_parlay_unpriced_response_keeps_price_none():
    """``price`` is sent WITHOUT omitempty: an unpriceable slip is an explicit
    null plus a ``reason``, not a missing key. A caller reading
    ``result.parlay.price.odds_american`` unguarded must fail loudly here."""
    result = ParlayPrice.model_validate(
        _payload("parlay_price_unpriced_contract.json")["data"]
    )
    assert result.parlay.price is None
    assert result.parlay.reason == "mutually_exclusive"
    assert result.parlay.conflicting_legs == [[0, 1]]
    assert result.warnings == ["one or more legs are live; quotes move fast"]


def test_parlay_note_is_always_present():
    """The model note is the standing guard against a modeled combined price
    being read as a bookable sportsbook quote — it must never be optional."""
    for fixture in ("parlay_price_contract.json", "parlay_price_unpriced_contract.json"):
        result = ParlayPrice.model_validate(_payload(fixture)["data"])
        assert "not a sportsbook parlay quote" in result.parlay.note


# --------------------------------------------------------------------------- #
# The general guard, extended to the new models
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("model", "fixture", "extract"),
    [
        (Player, "players_contract.json", lambda rows: rows),
        (PredictionMarket, "prediction_markets_contract.json", lambda rows: rows),
        (
            PredictionMarketCategory,
            "prediction_market_categories_contract.json",
            lambda rows: rows,
        ),
        (
            Settlement,
            "settlements_contract.json",
            lambda page: page["settlements"],
        ),
    ],
    ids=["Player", "PredictionMarket", "PredictionMarketCategory", "Settlement"],
)
def test_no_required_field_is_absent_from_the_wire(model, fixture, extract):
    """A required field the wire never sends makes the endpoint unparseable.

    Same guard as ``test_wire_contract.py``, pointed at the new surfaces. For
    /settlements the rows live under an object, so ``extract`` reaches in.
    """
    data = _payload(fixture)["data"]
    payloads = extract(data)
    required = {n for n, f in model.model_fields.items() if f.is_required()}
    for payload in payloads:
        missing = {r for r in required if r not in payload}
        assert not missing, (
            f"{model.__name__} requires {sorted(missing)}, absent from the wire "
            f"payload — this endpoint cannot be parsed. Wire keys: {sorted(payload)}"
        )
