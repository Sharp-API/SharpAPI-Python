# Changelog

All notable changes to the `sharpapi` Python SDK are documented here.

## 0.3.2 — 2026-05-07

### Changed

- Update `Repository` and `Changelog` URLs in package metadata to use the
  canonical `SharpAPI-Python` repo name (was lowercase `sharpapi-python`,
  redirected by GitHub but worth making canonical on PyPI). Metadata-only
  release; no code changes.

## 0.3.1 — 2026-05-06

### Added — TeamRef metadata

`TeamRef` now exposes five additional optional fields:

- `logo` — full CDN URL. ~93% of teams are populated.
- `city` — e.g. `"Arizona"` for the Diamondbacks.
- `mascot` — e.g. `"Diamondbacks"`.
- `conference` — e.g. `"NL"`, `"AFC"`, `"Western"`.
- `division` — e.g. `"West Division"`, `"NL East"`, `"Pacific Division"`.

All five default to `None` and are additive — existing 0.3.0 code keeps
working unchanged.

## 0.3.0 — 2026-05-06

### Added — nested refs

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
