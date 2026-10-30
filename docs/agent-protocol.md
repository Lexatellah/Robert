# Robert agent protocol

**Version:** 1 (v0.11).

An agent answers one question from one source and returns a normalized
list of transfer records. It does not correlate, score, or label.
It does not persist anything. It does not make network calls outside
`robert.http`. It does not know about other agents.

## The protocol

    from robert.agents.base import Agent

    class MyAgent(Agent):
        name = "my-agent"
        chains = ("ethereum", "bitcoin")

        def fetch(self, address, chain):
            # return list[dict] of normalized transfers
            ...

`fetch(address, chain)` must:

1. Raise `ValueError` if `chain not in self.chains`.
2. Raise `RuntimeError` (or let `robert.http` raise) on network failure.
   Do not swallow exceptions.
3. Return a `list[dict]`, empty list if no history. Never `None`.
4. Use `robert.http.get` / `robert.http.post_json` for network access.

## Normalized transfer record

Required keys: `hash`, `from`, `to`, `value`, `decimals`, `symbol`,
`timeStamp`, `chain`, `source`.

`value` is a string of raw base units (e.g. "1000000" for 1 USDT).
Never a float. `int(value) / 10**decimals` is the only correct reader.

Optional keys preserved: `kind`, `token_address`, `raw_inputs`,
`raw_outputs`. Unknown keys are ignored downstream, not removed.

## What the runner does

The runner skips the agent if `supports(chain)` is False, checks a
circuit breaker (3 failures open for 120s), calls `fetch`, records
success or failure, dedupes by `(hash, symbol)`, and stops at the first
agent that returns a non-empty list. You handle none of that.

## Rejected in review

- Returning `None` instead of an empty list.
- `try/except: pass` around the fetch.
- Direct `requests` calls bypassing `robert.http`.
- Module-level caches or any global state that changes across runs.
- Non-deterministic ordering or a timestamp captured at import.

## Testing

Put a trimmed response in `tests/fixtures/{name}/` (max 10 records)
and add `tests/test_agents_{name}.py` that mocks `robert.http` and
asserts the normalized output. Do not test against the live network.

## Submitting

Add `robert/agents/{name}.py`, a fixture, a test, register in
`runner.py`, add the host to `robert/http.py` allowlist if new, run
`pytest tests -v` until green. Commit message:
`agent({name}): one-line description`.

