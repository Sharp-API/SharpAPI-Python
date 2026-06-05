# Review rules — sharpapi-python (official Python SDK)

Guidance for the automated Claude PR reviewer (`.github/workflows/claude-review.yml`).

## Severity
- **[Critical]** — bug, a backward-incompatible change to the public API, or a type error.
- **[Important]** — a real problem to fix before merge.
- **[Nit]** — minor/style. Skip what `ruff` already enforces.

## Always check
- **Backward compatibility** — public classes/functions/kwargs are a published contract (PyPI is immutable). Flag any breaking change.
- **Types** — passes `pyright`; accurate annotations; no `Any` leakage in public signatures.
- **httpx / pydantic** — correct async/sync usage, error handling, model validation.
- **API parity** — the SDK matches the documented SharpAPI surface (endpoints, params, response models).

## Don't
- Don't flag pre-existing code this PR didn't touch.
- You MAY run `ruff check` / `pyright` to confirm a concern; otherwise don't speculate — cite `file:line` or omit. "LGTM" is valid.
