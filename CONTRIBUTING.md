# Contributing to Robert

Read these first:

- `GOVERNANCE.md` — non-negotiable principles.
- `docs/agent-protocol.md` — the spec for data sources.

## What we want

1. **Agents** — new keyless sources. See the protocol doc.
2. **Tests** — correlation edge cases, agent fixtures, property tests.
3. **Docs** — especially real-data validation of split detection.
4. **Bug reports with reproduction** — command, expected, actual, exit code.

## What we do not want

1. LLM in the data path. Robert is deterministic on purpose.
2. Scraping with fake keys or bypassing rate limits.
3. Anything that deanonymizes.
4. Speculative features. Open an issue, not a PR.

## Submit

    git checkout -b my-change
    python -m pytest tests -v
    git commit -m "agent(my-source): description"
    git push -u origin my-change

Open a PR. CI runs. If red, fix and push again.

## Commit style

- `agent({name}): what it adds`
- `fix({module}): what was broken`
- `test({module}): what it covers`
- `docs: what changed`

No emoji. No WIP. Every commit on `main` is meant to be shippable.

