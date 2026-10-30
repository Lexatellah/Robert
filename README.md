# Robert

[![test](https://github.com/Lexatellah/Robert/actions/workflows/test.yml/badge.svg)](https://github.com/Lexatellah/Robert/actions/workflows/test.yml)

**Open-source evidence engine for financial-scam victims.** Not a black
box. Never deanonymizes. Produces a reproducible, signed, tamper-evident
bundle from public blockchain data plus victim-supplied bank evidence.

## What Robert is

- **Keyless.** Public explorers and public RPC endpoints only.
- **Victim-first.** Built for the person who was scammed.
- **Tamper-evident.** Hash-chained audit log plus Ed25519 signature.
- **Honest about uncertainty.** Every assertion carries a tier and source.
- **Knows what it is looking at.** `detect` classifies bank vs crypto.

## What Robert is not

- **Not a bank tracer.** Bank leg is victim-supplied evidence only.
- **Not a deanonymizer.** Never outputs a real-world identity.
- **Not unhackable.** Tamper-evident and fail-closed is the actual claim.

## Supported chains (v0.8)

| Chain | Detect | Trace |
|---|---|---|
| EVM (Ethereum, Base, Arbitrum, Optimism, Polygon, ...) | yes | yes |
| Bitcoin | yes | yes |
| Tron | detected only | not yet |

v0.8 adds split-transfer aggregation. See `docs/v0.8-split-transfer.md`.

## Install

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install requests cryptography pytest pycryptodome

## CLI

    robert detect   INPUT...
    robert validate INPUT
    robert report   --address A --iban I --amount N --when T --out FILE
    robert verify   FILE

Exit codes: 0 ok, 2 invalid input, 3 no data.

## Verify a bundle

    python -m robert.cli verify bundle.zip

Re-checks file hashes, the audit hash chain, and the Ed25519 signature.

## Architecture

    robert/   domain, detect, assertions, audit, bank, bundle, correlate,
              split, rates, verify, http, security, cli, agents/
    docs/     v0.8-split-transfer.md
    tests/    test_correlate.py, test_split.py

## Contributing

Read GOVERNANCE.md first. Tier discipline, source provenance, no
deanonymization.

## License

AGPL-3.0. Forks stay open.
