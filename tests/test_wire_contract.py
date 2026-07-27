"""Model <-> wire contract, pinned against captured live payloads.

Issue #18: two model/wire mismatches shipped undetected because nothing here ever
parsed a real response.

- ``MiddleSide`` declared a required ``odds: OddsValue``. The wire sends odds
  **flat**. Every ``client.middles()`` call raised ``ValidationError`` — loud, but
  only at runtime, in a user's process.
- ``EVOpportunity.confidence_score`` had no alias for the wire's ``confidence``, so
  it silently read ``None`` on every row. Consumers filtering on it got nothing and
  no error.

The second kind is the reason these tests exist. A missing required field announces
itself; a field that quietly never populates does not, and no amount of unit testing
against hand-written dicts will catch it — the hand-written dict is written from the
same wrong belief as the model.

Fixtures are real responses captured from the deployed API (``tests/fixtures``).
Refresh them when the wire changes on purpose; a failure here means the wire moved
and the models did not.

Deliberately *not* asserted: "every declared field is populated by some payload."
That check was written and dropped — a small fixture cannot distinguish "the SDK
declares a field the wire never sends" from "this sample happened not to include a
conditional field." It flagged ``sharp_odds_american``, ``is_suspended`` and the
``*_ref`` objects, all of which are legitimately conditional. Catching the
``confidence_score`` class generically needs the full field space, not two rows;
until then it is pinned explicitly above.
"""

import json
import re
from pathlib import Path

import pytest

from sharpapi.models import EVOpportunity, MiddleOpportunity, MiddleSide

FIXTURES = Path(__file__).parent / "fixtures"


def _rows(name: str) -> list[dict]:
    payload = json.loads((FIXTURES / name).read_text())
    rows = payload.get("data") or []
    assert rows, f"{name} has no rows — recapture it, an empty fixture asserts nothing"
    return rows


def _sides(rows: list[dict]) -> list[dict]:
    return [s for r in rows for k in ("side1", "side2") if (s := r.get(k))]


# --------------------------------------------------------------------------- #
# Regression guards for the two shipped defects
# --------------------------------------------------------------------------- #


def test_middles_response_parses():
    """The #18 headline: this raised ValidationError on every real payload."""
    for row in _rows("middles_live.json"):
        MiddleOpportunity.model_validate(row)


def test_middle_side_reads_flat_odds():
    for side in _sides(_rows("middles_live.json")):
        parsed = MiddleSide.model_validate(side)
        assert parsed.odds_american == side["odds_american"]
        assert parsed.odds_decimal == side["odds_decimal"]


def test_ev_confidence_score_populates_from_wire_confidence():
    """Wire sends ``confidence``; the public attribute stayed ``confidence_score``."""
    for row in _rows("ev_live.json"):
        if (wire := row.get("confidence")) is None:
            continue
        assert EVOpportunity.model_validate(row).confidence_score == pytest.approx(wire)
        break
    else:
        pytest.skip("no row carried `confidence`")


def test_ev_quality_tier_populates():
    for row in _rows("ev_live.json"):
        if (wire := row.get("quality_tier")) is None:
            continue
        assert EVOpportunity.model_validate(row).quality_tier == wire
        break
    else:
        pytest.skip("no row carried `quality_tier`")


# --------------------------------------------------------------------------- #
# The general guard — catches the next one of these, not just these two
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("model", "fixture", "extract"),
    [
        (MiddleSide, "middles_live.json", _sides),
        (EVOpportunity, "ev_live.json", lambda rows: rows),
    ],
    ids=["MiddleSide", "EVOpportunity"],
)
def test_no_required_field_is_absent_from_the_wire(model, fixture, extract):
    """A required field the wire never sends makes the endpoint unparseable.

    This is the shape of the ``MiddleSide.odds`` bug, stated generally.
    """
    payloads = extract(_rows(fixture))
    required = {n for n, f in model.model_fields.items() if f.is_required()}
    for payload in payloads:
        missing = {
            r
            for r in required
            if r not in payload and not _satisfied_by_alias(model, r, payload)
        }
        assert not missing, (
            f"{model.__name__} requires {sorted(missing)}, absent from a live payload "
            f"— this endpoint cannot be parsed. Wire keys: {sorted(payload)}"
        )


def _satisfied_by_alias(model, field_name: str, payload: dict) -> bool:
    alias = model.model_fields[field_name].validation_alias
    if alias is None:
        return False
    choices = getattr(alias, "choices", None)
    if choices is None:
        return isinstance(alias, str) and alias in payload
    return any(isinstance(c, str) and c in payload for c in choices)


# --------------------------------------------------------------------------- #
# Version declarations are also a wire contract — with the packaging metadata
# --------------------------------------------------------------------------- #


def test_dunder_version_matches_pyproject():
    """``__version__`` and ``pyproject.toml`` are two declarations of one fact.

    They drifted: #13 bumped ``pyproject.toml`` 0.4.0 -> 0.4.1 and left
    ``__init__.py`` at 0.4.0, so the published 0.4.1 sdist reports
    ``sharpapi.__version__ == "0.4.0"``. PyPI is immutable, so that wrong answer is
    permanent for 0.4.1 — this test only stops the next one.

    Compares the two *sources*, not ``importlib.metadata``. Dist metadata is only as
    fresh as the last ``pip install``; a stale editable install reports whatever it
    was built at (0.2.0 on this dev box), which would make this test pass in CI and
    fail locally for a reason that has nothing to do with the bug.
    """
    import sharpapi

    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    declared = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert declared, "no version in pyproject.toml"
    assert sharpapi.__version__ == declared.group(1)
