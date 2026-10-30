from datetime import datetime, timezone

def correlate(bank_leg, crypto_leg, amount_tolerance_pct=1.0, window_hours=72):
    matches = []
    lo = bank_leg["amount"] * (1 - amount_tolerance_pct / 100)
    hi = bank_leg["amount"] * (1 + amount_tolerance_pct / 100)
    t0 = bank_leg["sent_at"] - window_hours * 3600
    t1 = bank_leg["sent_at"] + window_hours * 3600
    for tx in crypto_leg:
        try:
            value = int(tx["value"]) / 10**18
            ts = int(tx["timeStamp"])
        except Exception:
            continue
        if lo <= value <= hi and t0 <= ts <= t1:
            matches.append({
                "tx_hash": tx["hash"],
                "value": value,
                "time": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                "note": "amount+time correlation only; not proof of same funds",
            })
    return matches
