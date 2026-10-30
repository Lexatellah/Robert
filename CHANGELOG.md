# Changelog

## v0.9 - sort-before-combine
- `robert/split.py`: ranks all combinations across all set sizes by
  sum-fit to the bank amount, then evaluates the top `max_sets`.
  Fixes the v0.8 false-negative where a true 3-leg split could be
  buried under hundreds of size-2 combinations.
- `tests/test_split.py`: adds `test_late_split_is_found_after_sorting`
  (true split found amid 37 decoy legs) and
  `test_split_still_bounded_after_sorting` (bound holds, no flood).
- docs/v0.8-split-transfer.md §8 updated to describe the resolution.

## v0.8 - split-transfer aggregation
- `robert/split.py`: bounded subset-sum over on-chain legs (max 5, +/-1%, +/-72h). Called only when `correlate()` returns zero.
- `robert/cli.py`: wires split fallback into `report`.
- `tests/test_split.py`: 6 tests covering match, tolerance, window, 6-leg rejection, 1-leg deferral, missing rate.

## v0.7 - cross-asset correlation
- `robert/rates.json` + `robert/rates.py`: static EUR conversion; `--live-rate` opt-in.
- `robert/correlate.py`: EUR-equivalent match, +/-72h, `--window-hours`.
- `tests/test_correlate.py`: 4 tests.

## v0.6 - bundle verification
- `robert/verify.py`: re-checks file hashes, audit chain, Ed25519 signature over `signed_payload_sha256`.

## v0.5 - ERC-20 tokens
- `robert/agents/tokens.py`: Blockscout `/token-transfers` (keyless).
- Decimal-aware assertions.

## v0.4 - Bitcoin tracing
- `robert/agents/blockchair.py`: keyless Blockchair.
- `LICENSE` (AGPL-3.0), `demo.py`, `webui.py`.

## v0.3 - typed subjects
- `robert/domain.py`, `robert/detect.py`; `detect`/`validate`/`report` verbs.

## v0.2 - hardening
- `robert/http.py`, `robert/security.py`, `robert/audit.py`, signed bundles.

## v0.1 - initial CLI
- `report` with Etherscan, IBAN validation, signed bundle.
