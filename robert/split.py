"""Split-transfer aggregation (v0.8, fixed v0.9)."""
from __future__ import annotations
from datetime import datetime
from itertools import combinations
from robert import rates as R

NOTE = ("sum matches; split pattern consistent with mule behaviour; "
        "not proof of same funds")


def _ts(leg):
    v = leg.get("timeStamp")
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        if "T" in v:
            return int(datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp())
        return int(v)
    raise ValueError("no timestamp")


def _to_eur(leg, table):
    raw = int(leg["value"])
    dec = int(leg.get("decimals", 18))
    human = raw / 10**dec
    sym = leg.get("symbol", "ETH")
    return human, R.to_eur(human, sym, table)


def find_split_candidates(bank_leg, crypto_legs, rate_table,
                          window_hours=72, tolerance_pct=1.0,
                          max_legs=5, max_sets=50):
    bank_amount = float(bank_leg["amount"])
    ccy = bank_leg.get("currency", "EUR")
    if ccy != "EUR":
        bank_amount = R.to_eur(bank_amount, ccy, rate_table)
    lo = bank_amount * (1 - tolerance_pct / 100)
    hi = bank_amount * (1 + tolerance_pct / 100)
    t0 = int(bank_leg["sent_at"]) - window_hours * 3600
    t1 = int(bank_leg["sent_at"]) + window_hours * 3600

    usable = []
    for leg in crypto_legs:
        try:
            ts = _ts(leg)
            human, eur = _to_eur(leg, rate_table)
        except (KeyError, ValueError, TypeError):
            continue
        if not (t0 <= ts <= t1):
            continue
        usable.append({"tx_hash": leg["hash"], "symbol": leg.get("symbol", "ETH"),
                       "human_value": human, "eur_value": eur, "chain_ts": ts})

    if len(usable) < 2:
        return []

    # v0.9: score every combination across every size by sum-fit, then
    # take the top max_sets. Ranking by fit means a true 3-leg split is
    # not buried under hundreds of pairs.
    scored = []
    for size in range(2, min(max_legs, len(usable)) + 1):
        for combo in combinations(usable, size):
            total = sum(c["eur_value"] for c in combo)
            scored.append((abs(total - bank_amount), combo, total))
    scored.sort(key=lambda x: x[0])

    out = []
    for _, combo, total in scored[:max_sets]:
        if lo <= total <= hi:
            out.append(_make_candidate(combo, bank_amount, total,
                                       rate_table, bank_leg))

    uniq = {}
    for c in out:
        key = tuple(sorted(x["tx_hash"] for x in c["components"]))
        uniq.setdefault(key, c)
    return list(uniq.values())


def _make_candidate(combo, bank_amount, total_eur, rate_table, bank_leg):
    deltas = [c["chain_ts"] - int(bank_leg["sent_at"]) for c in combo]
    return {
        "kind": "correlation_candidate",
        "note": NOTE,
        "bank_eur": round(bank_amount, 2),
        "sum_eur": round(total_eur, 2),
        "legs": len(combo),
        "components": [
            {"tx_hash": c["tx_hash"], "symbol": c["symbol"],
             "human_value": c["human_value"],
             "eur_value": round(c["eur_value"], 2),
             "chain_ts": c["chain_ts"]}
            for c in combo
        ],
        "delta_seconds": {"min": min(deltas), "max": max(deltas)},
        "rate_source": rate_table.get("source", "static"),
        "rate_version": rate_table.get("version"),
    }
