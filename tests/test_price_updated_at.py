"""``price_updated_at`` (the per-row price change time) parses where the API sends it."""

from sharpapi import BestOddsSelection, OddsLine

ODDS = {
    "id": "o1", "sportsbook": "x", "event_id": "e1", "sport": "basketball",
    "league": "nba", "home_team": "A", "away_team": "B", "market_type": "moneyline",
    "selection": "A", "odds_american": -110, "odds_decimal": 1.91, "odds_probability": 0.52,
    "timestamp": "2026-11-18T02:00:05Z",
}


def test_odds_line_price_updated_at_present_and_absent():
    row = OddsLine.model_validate({**ODDS, "price_updated_at": "2026-11-17T22:41:00Z"})
    # A frozen price: the change time is hours older than the delivery timestamp,
    # and the two must not be confused.
    assert row.price_updated_at == "2026-11-17T22:41:00Z"
    assert row.timestamp == "2026-11-18T02:00:05Z"
    assert OddsLine.model_validate(ODDS).price_updated_at is None


def test_best_odds_selection_price_updated_at_present_and_absent():
    base = {"event_id": "e1", "best_book": "x", "timestamp": "2026-11-18T02:00:05Z"}
    sel = BestOddsSelection.model_validate({**base, "price_updated_at": "2026-11-17T22:41:00Z"})
    assert sel.price_updated_at == "2026-11-17T22:41:00Z"
    assert BestOddsSelection.model_validate(base).price_updated_at is None
