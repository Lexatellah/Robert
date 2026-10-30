"""Split-transfer aggregation (v0.8).

Design: docs/v0.8-split-transfer.md.
Contract:
  * min 2 legs, max 5 legs per candidate
  * every leg inside the +/-window_hours window
  * EUR-equivalent sum inside +/-tolerance_pct of bank amount
  * at most max_sets candidate sets evaluated (bounded search)
  * never returns a 1-leg match (that is correlate()'s job)
"""
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


def _sort_by_proximity(legs, bank_eur, max_legs):
    """Order legs so combinations evaluate most-plausible sets first.
    For each candidate set size n in [2..max_legs], target per-leg value
    is bank_eur/n; sort ascending by distance from that target."""
    order = []
    for n in range(2, min(max_legs, len(legs)) + 1):
        target = bank_eur / n
        ranked = sorted(legs, key=lambda c: abs(c["eur_value"] - target))
        for leg in ranked:
            if leg not in order:
                order.append(leg)
    for leg in legs:
        if leg not in order:
            order.append(leg)
    return order

def find_split_candidates(bank_leg, crypto_legs, rate_table,
                          window_hours=72, tolerance_pct=1.0,
                          max_legs=5, max_sets=50):
    bank_amount = float(bank_leg["amount"])
    bank_ccy = bank_leg.get("currency", "EUR")
    if bank_ccy != "EUR":
        bank_amount = R.to_eur(bank_amount, bank_ccy, rate_table)
    lo = bank_amount * (1 - tolerance_pct / 100)
    hi = bank_amount * (1 + tolerance_pct / 100)
    t0 = int(bank_leg["sent_at"]) - window_hours * 3600
    t1 = int(bank_leg["sent_at"]) + window_hours * 3600

    # Filter to legs with a rate and a timestamp inside the window
    usable = []
    for leg in crypto_legs:
        try:
            ts = _ts(leg)
            human, eur = _to_eur(leg, rate_table)
        except (KeyError, ValueError, TypeError):
            continue
        if not (t0 <= ts <= t1):
            continue
        usable.append({
            "tx_hash": leg["hash"],
            "symbol": leg.get("symbol", "ETH"),
            "human_value": human,
            "eur_value": eur,
            "chain_ts": ts,
        })

    if len(usable) < 2:
        return []

    # v0.9: evaluate combinations across ALL sizes, ranked by how close
    # their sum is to the bank amount. This finds a true 3-leg split even
    # when 780 possible pairs exist, because ranking is by fit, not by
    # set size.
    usable = _sort_by_proximity(usable, bank_amount, max_legs)

    scored = []
    for size in range(2, min(max_legs, len(usable)) + 1):
        for combo in combinations(usable, size):
            total = sum(c["eur_value"] for c in combo)
            scored.append((abs(total - bank_amount), combo, total))
    scored.sort(key=lambda x: x[0])

    candidates = []
    for _, combo, total in scored[:max_sets]:
        if lo <= total <= hi:
            candidates.append(_make_candidate(combo, bank_amount, total,
                                              rate_table, bank_leg))

    # Deduplicate by component set; keep the tightest fit if two sets overlap
    uniq = {}
    for c in candidates:
        key = tuple(sorted(x["tx_hash"] for x in c["components"]))
        if key not in uniq:
            uniq[key] = c
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
