import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from robert.correlate import correlate
from robert import rates


def _leg(h, sym, raw, dec, ts):
    return {"hash": h, "symbol": sym, "value": str(raw), "decimals": dec,
            "timeStamp": ts, "from": "0xa", "to": "0xb"}


def test_correlation_fires_on_eur_equivalent_match():
    table = rates.load_rates()
    legs = [
        _leg("0xaaa", "USDT", 100_000_000, 6, 1730000000 + 60),   # 100 USDT
        _leg("0xbbb", "USDT", 500_000_000, 6, 1730000000 + 120),  # 500 USDT
    ]
    bank = {"amount": 92.0, "currency": "EUR",
            "sent_at": 1730000000, "iban": "DE89"}
    matches = correlate(bank, legs, window_hours=1, rate_table=table)
    assert len(matches) == 1
    m = matches[0]
    assert m["tx_hash"] == "0xaaa"
    assert m["symbol"] == "USDT"
    assert m["kind"] == "correlation_candidate"
    assert m["delta_seconds"] == 60


def test_correlation_excludes_out_of_window():
    table = rates.load_rates()
    legs = [_leg("0xaaa", "USDT", 100_000_000, 6, 1730000000 + 7200)]  # +2h
    bank = {"amount": 92.0, "currency": "EUR",
            "sent_at": 1730000000, "iban": "DE89"}
    matches = correlate(bank, legs, window_hours=1, rate_table=table)
    assert matches == []


def test_correlation_excludes_out_of_tolerance():
    table = rates.load_rates()
    legs = [_leg("0xbbb", "USDT", 500_000_000, 6, 1730000000 + 60)]  # 500 USDT
    bank = {"amount": 92.0, "currency": "EUR",
            "sent_at": 1730000000, "iban": "DE89"}
    matches = correlate(bank, legs, window_hours=1, rate_table=table)
    assert matches == []


def test_correlation_note_is_the_fixed_string():
    table = rates.load_rates()
    legs = [_leg("0xaaa", "USDT", 100_000_000, 6, 1730000000)]
    bank = {"amount": 92.0, "currency": "EUR",
            "sent_at": 1730000000, "iban": "DE89"}
    m = correlate(bank, legs, window_hours=1, rate_table=table)[0]
    assert m["note"] == "amount+time match only; not proof of same funds"
