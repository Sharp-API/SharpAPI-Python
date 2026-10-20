"""``season_type`` field parsing and filter serialisation."""

import httpx

from sharpapi import Event, OddsLine, SharpAPI

EVENT = {"id": "e1", "sport": "basketball", "league": "nba", "home_team": "A", "away_team": "B"}
ODDS = {
    "id": "o1", "sportsbook": "x", "event_id": "e1", "sport": "basketball",
    "league": "nba", "home_team": "A", "away_team": "B", "market_type": "moneyline",
    "selection": "A", "odds_american": -110, "odds_decimal": 1.91, "odds_probability": 0.52,
}


def test_event_season_type_present_and_absent():
    assert Event.model_validate({**EVENT, "season_type": "Preseason"}).season_type == "Preseason"
    assert Event.model_validate(EVENT).season_type is None


def test_odds_season_type_present_and_absent():
    row = OddsLine.model_validate({**ODDS, "season_type": "Regular Season"})
    assert row.season_type == "Regular Season"
    assert OddsLine.model_validate(ODDS).season_type is None


def _client(seen):
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"success": True, "data": []})

    c = SharpAPI("sk_test")
    c._http = httpx.Client(base_url=c._http.base_url, transport=httpx.MockTransport(handler))
    return c


def test_filter_sent_on_events_and_odds():
    seen = []
    c = _client(seen)
    c.events.list(season_type="Preseason")
    c.odds.get(season_type="Regular Season")
    assert seen[0].url.params["season_type"] == "Preseason"
    assert seen[1].url.params["season_type"] == "Regular Season"


def test_filter_omitted_when_unset():
    seen = []
    c = _client(seen)
    c.events.list()
    c.odds.get()
    assert all("season_type" not in r.url.params for r in seen)


def test_stream_odds_carries_filter():
    stream = SharpAPI("sk_test").stream.odds(season_type="Preseason")
    assert "season_type=Preseason" in stream._url
