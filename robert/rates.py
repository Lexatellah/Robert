import json
from pathlib import Path

_DEFAULT = Path(__file__).parent / "rates.json"

def load_rates(path=None):
    p = Path(path) if path else _DEFAULT
    with open(p) as f:
        return json.load(f)

def to_eur(amount, symbol, rates):
    table = rates.get("to_eur", {})
    if symbol not in table:
        raise KeyError(f"no rate for {symbol}")
    return float(amount) * float(table[symbol])

def live_rate(symbol, http_mod):
    """Keyless CoinGecko lookup; returns EUR per unit or raises."""
    ids = {"BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether",
           "USDC": "usd-coin", "DAI": "dai", "BNB": "binancecoin",
           "MATIC": "matic-network"}
    cg = ids.get(symbol)
    if not cg:
        raise KeyError(f"no CoinGecko id for {symbol}")
    import json as _json
    body = http_mod.get(f"https://api.coingecko.com/api/v3/simple/price",
                        params={"ids": cg, "vs_currencies": "eur"})
    return float(_json.loads(body)[cg]["eur"])
