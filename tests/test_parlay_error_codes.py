"""Registry guards for the parlay error codes and /settlements' 503.

Kept apart from ``test_new_surfaces.py`` deliberately: this module imports
ONLY symbols that predate the change, so it still collects and runs against an
unpatched tree — which is what makes its failure there real evidence that the
registry entries are load-bearing. The surfaces module cannot do that; its
models do not exist before the change, so reverting the source turns it into a
collection error rather than an honest failure.
"""

import httpx
import pytest

from sharpapi._base import handle_errors
from sharpapi.exceptions import (
    ERROR_CODE_DESCRIPTIONS,
    ERROR_CODE_TO_EXCEPTION,
    SharpAPIError,
    ValidationError,
)

PARLAY_CODES = [
    "correlation_unsupported",
    "too_few_legs",
    "too_many_legs",
    "unknown_leg",
    "ambiguous_leg",
]


def _error_response(status: int, code: str) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json={"error": {"code": code, "message": "rejected"}},
        request=httpx.Request("POST", "https://api.sharpapi.io/api/v1/parlay/price"),
    )


@pytest.mark.parametrize("code", PARLAY_CODES)
def test_parlay_rejection_raises_validation_error(code):
    """The live path: every parlay rejection is a 400 carrying one of these
    codes, and the caller sees ``ValidationError`` with the code preserved.

    NOTE this alone is NOT a guard on the registry: ``handle_errors`` falls
    back to status routing, and 400 already routes to ``ValidationError``, so
    this passes with or without the mapping. The registry guards are
    ``test_parlay_code_is_authoritative_over_status`` and
    ``test_registry_carries_every_code`` below.
    """
    with pytest.raises(ValidationError) as exc:
        handle_errors(_error_response(400, code))
    assert type(exc.value) is ValidationError
    assert exc.value.code == code
    assert exc.value.status == 400


@pytest.mark.parametrize("code", PARLAY_CODES)
def test_parlay_code_is_authoritative_over_status(code):
    """Registering a code makes it, not the HTTP status, decide the class.

    Sent at 500 — a status whose fallback is the bare ``SharpAPIError`` —
    precisely so this fails when the code is missing from
    ``ERROR_CODE_TO_EXCEPTION``. On the wire these codes only ever arrive at
    400; the point here is which of the two inputs the SDK classifies on.
    """
    with pytest.raises(ValidationError) as exc:
        handle_errors(_error_response(500, code))
    assert type(exc.value) is ValidationError
    assert exc.value.code == code


def test_settlements_unavailable_raises_base_error():
    """A degraded grading store answers 503 ``service_unavailable``.

    It is deliberately NOT a ``RateLimitedError`` or ``ValidationError``: the
    caller's request was fine and there is no retry budget to read.
    """
    response = httpx.Response(
        status_code=503,
        json={"error": {"code": "service_unavailable", "message": "unavailable"}},
        request=httpx.Request("GET", "https://api.sharpapi.io/api/v1/settlements"),
    )
    with pytest.raises(SharpAPIError) as exc:
        handle_errors(response)
    assert type(exc.value) is SharpAPIError
    assert exc.value.code == "service_unavailable"
    assert exc.value.status == 503


@pytest.mark.parametrize("code", [*PARLAY_CODES, "service_unavailable"])
def test_registry_carries_every_code(code):
    """A code in the exception map with no description is a half-registration."""
    assert ERROR_CODE_TO_EXCEPTION[code] is not None
    assert ERROR_CODE_DESCRIPTIONS[code].strip()


