# Changelog

All notable changes to the `sharpapi` Python SDK are documented here.

## 0.3.0 — 2026-05-06

### Added — OpticOdds-parity nested refs (Phase 1f)

Every odds row, opportunity row, and reference-list row may now carry
optional structured reference objects alongside the existing flat fields.
All new fields are **optional and additive** — clients on older API
versions (or talking to older API servers) see `None` and behave
identically.

New models:

- `TeamRef` — `id`, `numerical_id`, `name`, `abbreviation` (latter only on
  team-sport competitors)
- `SportRef` — `id`, `name`, `numerical_id`
- `EntityRef` — `id`, `label`, `numerical_id` (used for league / market /
  sportsbook refs)

New optional fields:

- `OddsLine`, `EVOpportunity`, `ArbitrageOpportunity`, `MiddleOpportunity`,
  `LowHoldOpportunity` — all gain `home`, `away`, `sport_ref`, `league_ref`,
  `market_ref`, `sportsbook_ref` (legs / opps without a single book skip
  `sportsbook_ref`).
- `ArbitrageLeg` — gains `sportsbook_ref`.
- `ClosingOddsLine` — gains `market_ref`, `sportsbook_ref`.
- `ClosingSnapshot` — gains `home`, `away`, `sport_ref`, `league_ref`.
- `Sport`, `League`, `Sportsbook`, `Market` — gain `numerical_id`.
- `Event` — gains `home`, `away`, `sport_ref`, `league_ref`.

New reference model:

- `Team` — for the `/teams` reference endpoint, includes optional
  `abbreviation` and `numerical_id`.

### Backward compatibility

No existing field was renamed, retyped, or removed. Code that does not
reference the new attributes continues to work without changes.
