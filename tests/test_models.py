"""Tests for Pydantic response model parsing."""

from sharpapi._base import parse_response
from sharpapi.models import (
    ArbitrageOpportunity,
    EntityRef,
    EVOpportunity,
    League,
    LowHoldOpportunity,
    MiddleOpportunity,
    OddsLine,
    Sport,
    SportRef,
    Sportsbook,
    Team,
    TeamRef,
)

from .conftest import (
    ARBITRAGE_RESPONSE,
    EV_RESPONSE,
    LOW_HOLD_RESPONSE,
    MIDDLES_RESPONSE,
    ODDS_RESPONSE,
    SPORTS_RESPONSE,
)


class TestArbitrageModel:
    def test_parse_full_response(self):
        result = parse_response(ARBITRAGE_RESPONSE, ArbitrageOpportunity)
        assert len(result.data) == 1
        arb = result.data[0]
        assert arb.id == "arb_dk_pin_nba_lal_bos_ml"
        assert arb.profit_percent == 1.83
        assert arb.implied_total == 98.2
        assert arb.sport == "basketball"
        assert arb.league == "nba"
        assert arb.is_live is True
        assert arb.possibly_stale is False
        assert arb.warnings == ["LIVE_GAME"]

    def test_legs(self):
        result = parse_response(ARBITRAGE_RESPONSE, ArbitrageOpportunity)
        arb = result.data[0]
        assert len(arb.legs) == 2
        leg1 = arb.legs[0]
        assert leg1.sportsbook == "draftkings"
        assert leg1.selection == "Los Angeles Lakers"
        assert leg1.odds_american == 145
        assert leg1.odds_decimal == 2.45
        assert leg1.stake_percent == 41.5
        assert leg1.external_event_id == "dk_12345"

    def test_ev_cross_reference(self):
        result = parse_response(ARBITRAGE_RESPONSE, ArbitrageOpportunity)
        arb = result.data[0]
        assert arb.ev_available is True
        assert arb.ev_percentage == 3.2

    def test_meta(self):
        result = parse_response(ARBITRAGE_RESPONSE, ArbitrageOpportunity)
        assert result.meta is not None
        assert result.meta.pagination is not None
        assert result.meta.count == 1
        assert result.meta.pagination.limit == 50
        assert result.meta.pagination.has_more is False


class TestEVModel:
    def test_parse_full_response(self):
        result = parse_response(EV_RESPONSE, EVOpportunity)
        assert len(result.data) == 1
        ev = result.data[0]
        assert ev.ev_percentage == 4.2
        assert ev.selection == "PHO Suns"
        assert ev.sportsbook == "draftkings"
        assert ev.odds_american == -105
        assert ev.odds_decimal == 1.952

    def test_sharp_reference(self):
        result = parse_response(EV_RESPONSE, EVOpportunity)
        ev = result.data[0]
        assert ev.devig_method == "power"
        assert ev.sharp_book == "pinnacle"
        assert ev.no_vig_odds == 1.912
        assert ev.fair_probability == 0.523

    def test_scoring(self):
        result = parse_response(EV_RESPONSE, EVOpportunity)
        ev = result.data[0]
        assert ev.confidence_score == 87
        assert ev.kelly_percent == 0.021
        assert ev.book_count == 8

    def test_aliased_fields(self):
        result = parse_response(EV_RESPONSE, EVOpportunity)
        ev = result.data[0]
        # game_id -> event_id, game -> event_name, market -> market_type
        assert ev.event_id == "evt_123"
        assert ev.event_name == "PHI 76ers vs PHO Suns"
        assert ev.market_type == "moneyline"


class TestMiddlesModel:
    def test_parse_full_response(self):
        result = parse_response(MIDDLES_RESPONSE, MiddleOpportunity)
        assert len(result.data) == 1
        mid = result.data[0]
        assert mid.event_name == "Buffalo Bills @ Kansas City Chiefs"
        assert mid.middle_size == 5.0
        assert mid.middle_numbers == [3, 4, 5, 6, 7]
        assert mid.middle_probability == 0.377
        assert mid.quality_score == 85

    def test_sides(self):
        result = parse_response(MIDDLES_RESPONSE, MiddleOpportunity)
        mid = result.data[0]
        assert mid.side1.book == "draftkings"
        assert mid.side1.line == -2.5
        assert mid.side1.odds.american == -110
        assert mid.side2.book == "fanduel"
        assert mid.side2.line == 7.5

    def test_key_numbers(self):
        result = parse_response(MIDDLES_RESPONSE, MiddleOpportunity)
        mid = result.data[0]
        assert mid.key_numbers == [3, 7]


class TestLowHoldModel:
    def test_parse_response(self):
        result = parse_response(LOW_HOLD_RESPONSE, LowHoldOpportunity)
        assert len(result.data) == 1
        lh = result.data[0]
        assert lh.hold_percentage == 1.8
        assert lh.sport == "basketball"


class TestOddsLineModel:
    def test_parse_response(self):
        result = parse_response(ODDS_RESPONSE, OddsLine)
        assert len(result.data) == 1
        line = result.data[0]
        assert line.sportsbook == "draftkings"
        assert line.odds_american == 145
        assert line.odds_decimal == 2.45
        assert line.probability == 0.408
        assert line.home_team == "Boston Celtics"
        assert line.away_team == "Los Angeles Lakers"
        assert line.is_live is False


class TestSportModel:
    def test_parse_response(self):
        result = parse_response(SPORTS_RESPONSE, Sport)
        assert len(result.data) == 2
        assert result.data[0].name == "Basketball"
        assert result.data[1].slug == "football"


class TestEmptyResponse:
    def test_empty_data_array(self):
        result = parse_response({"data": []}, ArbitrageOpportunity)
        assert result.data == []
        assert result.meta is None

    def test_missing_optional_fields(self):
        minimal = {
            "data": [{
                "id": "arb_min",
                "event_name": "A vs B",
                "sport": "basketball",
                "market_type": "moneyline",
                "profit_percent": 0.5,
                "legs": [
                    {"sportsbook": "dk", "selection": "A", "odds_american": 100,
                     "odds_decimal": 2.0, "stake_percent": 50.0},
                    {"sportsbook": "fd", "selection": "B", "odds_american": 100,
                     "odds_decimal": 2.0, "stake_percent": 50.0},
                ],
            }],
        }
        result = parse_response(minimal, ArbitrageOpportunity)
        arb = result.data[0]
        assert arb.warnings == []
        assert arb.possibly_stale is False
        assert arb.is_player_prop is False


# =============================================================================
# Phase 1f — nested refs + numerical_id (OpticOdds parity)
# =============================================================================


# Pinnacle MLB sample with the structured ref objects fully populated.
PHASE_1F_NESTED_REFS = {
    "home": {
        "id": "new_york_yankees",
        "numerical_id": 20,
        "name": "New York Yankees",
        "abbreviation": "NYY",
    },
    "away": {
        "id": "boston_red_sox",
        "numerical_id": 5,
        "name": "Boston Red Sox",
        "abbreviation": "BOS",
    },
    "sport_ref": {"id": "baseball", "name": "Baseball", "numerical_id": 3},
    "league_ref": {"id": "mlb", "label": "MLB", "numerical_id": 354},
    "market_ref": {"id": "moneyline", "label": "Moneyline", "numerical_id": 878},
    "sportsbook_ref": {"id": "pinnacle", "label": "Pinnacle", "numerical_id": 28},
}


class TestPhase1fNestedRefsOddsLine:
    """OddsLine accepts the new structured ref objects when the API ships them."""

    def test_odds_line_with_nested_refs(self):
        payload = {
            "data": [
                {
                    "id": "pin_999_ml_NYY",
                    "sportsbook": "pinnacle",
                    "event_id": "evt_999",
                    "sport": "baseball",
                    "league": "mlb",
                    "home_team": "New York Yankees",
                    "away_team": "Boston Red Sox",
                    "market_type": "moneyline",
                    "selection": "New York Yankees",
                    "odds_american": -135,
                    "odds_decimal": 1.741,
                    "probability": 0.574,
                    "is_live": False,
                    **PHASE_1F_NESTED_REFS,
                }
            ]
        }
        result = parse_response(payload, OddsLine)
        line = result.data[0]
        # Legacy flat fields still parse exactly as before.
        assert line.home_team == "New York Yankees"
        assert line.away_team == "Boston Red Sox"
        assert line.sportsbook == "pinnacle"
        # New structured refs are populated.
        assert isinstance(line.home, TeamRef)
        assert line.home.id == "new_york_yankees"
        assert line.home.numerical_id == 20
        assert line.home.abbreviation == "NYY"
        assert isinstance(line.away, TeamRef)
        assert line.away.abbreviation == "BOS"
        assert isinstance(line.sport_ref, SportRef)
        assert line.sport_ref.numerical_id == 3
        assert isinstance(line.league_ref, EntityRef)
        assert line.league_ref.label == "MLB"
        assert line.league_ref.numerical_id == 354
        assert isinstance(line.market_ref, EntityRef)
        assert line.market_ref.id == "moneyline"
        assert isinstance(line.sportsbook_ref, EntityRef)
        assert line.sportsbook_ref.numerical_id == 28

    def test_odds_line_legacy_no_refs(self):
        """Legacy server (no nested refs) keeps working — every ref is None."""
        payload = {
            "data": [
                {
                    "id": "pin_999_ml_NYY",
                    "sportsbook": "pinnacle",
                    "event_id": "evt_999",
                    "sport": "baseball",
                    "league": "mlb",
                    "home_team": "New York Yankees",
                    "away_team": "Boston Red Sox",
                    "market_type": "moneyline",
                    "selection": "New York Yankees",
                    "odds_american": -135,
                    "odds_decimal": 1.741,
                    "probability": 0.574,
                    "is_live": False,
                }
            ]
        }
        result = parse_response(payload, OddsLine)
        line = result.data[0]
        assert line.home is None
        assert line.away is None
        assert line.sport_ref is None
        assert line.league_ref is None
        assert line.market_ref is None
        assert line.sportsbook_ref is None
        # Legacy fields untouched.
        assert line.home_team == "New York Yankees"
        assert line.sportsbook == "pinnacle"


class TestPhase1fNestedRefsOpportunities:
    """EV / arbitrage / middle / low-hold rows surface nested refs the same way."""

    def test_ev_opportunity_with_nested_refs(self):
        payload = {
            "data": [
                {
                    "id": "ev_pin_mlb_999_ml_NYY",
                    "event_id": "evt_999",
                    "sport": "baseball",
                    "league": "mlb",
                    "selection": "New York Yankees",
                    "sportsbook": "pinnacle",
                    "odds_american": -135,
                    "odds_decimal": 1.741,
                    "ev_percentage": 3.1,
                    **PHASE_1F_NESTED_REFS,
                }
            ]
        }
        ev = parse_response(payload, EVOpportunity).data[0]
        assert ev.home is not None and ev.home.id == "new_york_yankees"
        assert ev.sport_ref is not None and ev.sport_ref.numerical_id == 3
        assert ev.league_ref is not None and ev.league_ref.label == "MLB"
        assert ev.market_ref is not None and ev.market_ref.numerical_id == 878
        assert ev.sportsbook_ref is not None and ev.sportsbook_ref.id == "pinnacle"

    def test_arbitrage_with_nested_refs_and_per_leg_book_ref(self):
        payload = {
            "data": [
                {
                    "id": "arb_pin_dk_mlb",
                    "event_name": "Boston Red Sox @ New York Yankees",
                    "sport": "baseball",
                    "market_type": "moneyline",
                    "profit_percent": 1.2,
                    "legs": [
                        {
                            "sportsbook": "pinnacle",
                            "selection": "New York Yankees",
                            "odds_american": -135,
                            "odds_decimal": 1.741,
                            "stake_percent": 58.5,
                            "sportsbook_ref": {
                                "id": "pinnacle",
                                "label": "Pinnacle",
                                "numerical_id": 28,
                            },
                        },
                        {
                            "sportsbook": "draftkings",
                            "selection": "Boston Red Sox",
                            "odds_american": 145,
                            "odds_decimal": 2.45,
                            "stake_percent": 41.5,
                            "sportsbook_ref": {
                                "id": "draftkings",
                                "label": "DraftKings",
                                "numerical_id": 4,
                            },
                        },
                    ],
                    **PHASE_1F_NESTED_REFS,
                }
            ]
        }
        arb = parse_response(payload, ArbitrageOpportunity).data[0]
        assert arb.home is not None and arb.home.abbreviation == "NYY"
        assert arb.market_ref is not None and arb.market_ref.id == "moneyline"
        # Each leg carries its own sportsbook_ref.
        assert arb.legs[0].sportsbook_ref is not None
        assert arb.legs[0].sportsbook_ref.numerical_id == 28
        assert arb.legs[1].sportsbook_ref is not None
        assert arb.legs[1].sportsbook_ref.id == "draftkings"

    def test_middles_with_nested_refs(self):
        payload = {
            "data": [
                {
                    "id": "mid_001",
                    "event_name": "Boston Red Sox @ New York Yankees",
                    "sport": "baseball",
                    "league": "mlb",
                    "market_type": "moneyline",
                    **PHASE_1F_NESTED_REFS,
                }
            ]
        }
        mid = parse_response(payload, MiddleOpportunity).data[0]
        assert mid.away is not None and mid.away.id == "boston_red_sox"
        assert mid.league_ref is not None and mid.league_ref.numerical_id == 354

    def test_low_hold_with_nested_refs(self):
        payload = {
            "data": [
                {
                    "id": "lh_001",
                    "event_name": "Boston Red Sox @ New York Yankees",
                    "sport": "baseball",
                    "market_type": "moneyline",
                    "hold_percentage": 1.4,
                    **PHASE_1F_NESTED_REFS,
                }
            ]
        }
        lh = parse_response(payload, LowHoldOpportunity).data[0]
        assert lh.home is not None and lh.home.numerical_id == 20
        assert lh.sport_ref is not None and lh.sport_ref.id == "baseball"


class TestPhase1fReferenceEndpointNumericalIds:
    """Reference endpoints (sports / leagues / sportsbooks / teams) gain numerical_id."""

    def test_sport_with_numerical_id(self):
        payload = {"data": [{
            "id": "baseball", "name": "Baseball", "slug": "baseball",
            "active": True, "numerical_id": 3,
        }]}
        sport = parse_response(payload, Sport).data[0]
        assert sport.numerical_id == 3
        assert sport.name == "Baseball"

    def test_sport_legacy_no_numerical_id(self):
        payload = {"data": [{
            "id": "baseball", "name": "Baseball", "slug": "baseball", "active": True,
        }]}
        sport = parse_response(payload, Sport).data[0]
        assert sport.numerical_id is None

    def test_league_with_numerical_id(self):
        payload = {"data": [{
            "id": "mlb", "name": "MLB", "slug": "mlb",
            "sport_id": "baseball", "active": True, "numerical_id": 354,
        }]}
        league = parse_response(payload, League).data[0]
        assert league.numerical_id == 354

    def test_sportsbook_with_numerical_id(self):
        payload = {"data": [{
            "id": "pinnacle", "name": "Pinnacle", "slug": "pinnacle",
            "active": True, "numerical_id": 28,
        }]}
        book = parse_response(payload, Sportsbook).data[0]
        assert book.numerical_id == 28

    def test_team_with_abbreviation_and_numerical_id(self):
        payload = {"data": [{
            "id": "new_york_yankees",
            "name": "New York Yankees",
            "sport": "baseball",
            "league": "mlb",
            "abbreviation": "NYY",
            "numerical_id": 20,
        }]}
        team = parse_response(payload, Team).data[0]
        assert team.abbreviation == "NYY"
        assert team.numerical_id == 20

    def test_team_without_abbreviation(self):
        """Individual-sport competitors (tennis players, fighters) skip abbreviation."""
        payload = {"data": [{
            "id": "novak_djokovic",
            "name": "Novak Djokovic",
            "sport": "tennis",
            "numerical_id": 9001,
        }]}
        team = parse_response(payload, Team).data[0]
        assert team.abbreviation is None
        assert team.numerical_id == 9001


class TestPhase2cTeamMetadata:
    """TeamRef carries the OpticOdds-sourced metadata fields backfilled by
    api-adapters PR #499: logo / city / mascot / conference / division.
    All five are optional — present for ~93% of teams (logo) with similar
    coverage on the rest. The atlas ``nickname`` field is intentionally
    NOT exposed as a model attribute because it duplicates ``mascot``.
    """

    def test_teamref_with_full_phase2c_metadata(self):
        ref = TeamRef.model_validate({
            "id": "arizona_diamondbacks",
            "numerical_id": 1,
            "name": "Arizona Diamondbacks",
            "abbreviation": "ARI",
            "logo": "https://cdn.opticodds.com/team-logos/baseball/18.png",
            "city": "Arizona",
            "mascot": "Diamondbacks",
            "conference": "NL",
            "division": "West Division",
        })
        assert ref.logo == "https://cdn.opticodds.com/team-logos/baseball/18.png"
        assert ref.city == "Arizona"
        assert ref.mascot == "Diamondbacks"
        assert ref.conference == "NL"
        assert ref.division == "West Division"

    def test_teamref_phase2c_fields_optional(self):
        """Servers that haven't shipped Phase 2c yet keep working — every
        new field defaults to None and the legacy fields parse normally.
        """
        ref = TeamRef.model_validate({
            "id": "novak_djokovic",
            "numerical_id": 9001,
            "name": "Novak Djokovic",
        })
        assert ref.logo is None
        assert ref.city is None
        assert ref.mascot is None
        assert ref.conference is None
        assert ref.division is None
        # Legacy attributes still resolve correctly.
        assert ref.id == "novak_djokovic"
        assert ref.numerical_id == 9001

    def test_teamref_serialization_omits_unset_phase2c_fields(self):
        """``model_dump(exclude_none=True)`` keeps the wire compact for
        rows missing the optional metadata — i.e. our request bodies and
        round-trip serialization don't pollute output with null logos.
        """
        ref = TeamRef(
            id="los_angeles_lakers",
            numerical_id=206,
            name="Los Angeles Lakers",
            abbreviation="LAL",
        )
        dumped = ref.model_dump(exclude_none=True)
        assert "logo" not in dumped
        assert "city" not in dumped
        assert "mascot" not in dumped
        assert "conference" not in dumped
        assert "division" not in dumped
        assert dumped["abbreviation"] == "LAL"
