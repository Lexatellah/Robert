from datetime import datetime, timezone
from robert import rates as R

def correlate(bank_leg, crypto_leg, amount_tolerance_pct=1.0,
              window_hours=72, rate_table=None):
    """
    Join a victim's bank transfer to on-chain flows by EUR-equivalent amount + time.
    Never a verdict. Every match records how it was computed.
    """
    table = rate_table or R.load_rates()
    bank_amount = float(bank_leg["amount"])
    bank_ccy = bank_leg.get("currency", "EUR")
    if bank_ccy != "EUR":
        bank_amount = R.to_eur(bank_amount, bank_ccy, table)
    lo = bank_amount * (1 - amount_tolerance_pct / 100)
    hi = bank_amount * (1 + amount_tolerance_pct / 100)
    t0 = int(bank_leg["sent_at"]) - window_hours * 3600
    t1 = int(bank_leg["sent_at"]) + window_hours * 3600

    matches = []
    for tx in crypto_leg:
        try:
            raw = int(tx["value"])
            decimals = int(tx.get("decimals", 18))
            human = raw / 10**decimals
            symbol = tx.get("symbol", "ETH")
            ts = tx.get("timeStamp")
            if isinstance(ts, str):
                if "T" in ts:
                    ts = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
                else:
                    ts = int(ts)
            eur = R.to_eur(human, symbol, table)
        except (KeyError, ValueError, TypeError):
            continue
        if lo <= eur <= hi and t0 <= ts <= t1:
            matches.append({
                "tx_hash": tx["hash"],
                "symbol": symbol,
                "human_value": human,
                "eur_value": round(eur, 2),
                "chain_ts": ts,
                "chain_time": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                "bank_ts": int(bank_leg["sent_at"]),
                "delta_seconds": ts - int(bank_leg["sent_at"]),
                "rate_source": table.get("source", "static"),
                "rate_version": table.get("version"),
                "kind": "correlation_candidate",
                "note": "amount+time match only; not proof of same funds",
            })
    return matches
