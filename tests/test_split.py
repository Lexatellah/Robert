import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from robert.split import find_split_candidates
from robert import rates


def _leg(h, sym, human, ts):
    """Build a leg with a decimal that matches common tokens."""
    dec = {"USDT": 6, "USDC": 6, "DAI": 18, "ETH": 18, "BTC": 8}.get(sym, 18)
    raw = int(round(human * 10**dec))
    return {"hash": h, "symbol": sym, "value": str(raw), "decimals": dec,
            "timeStamp": ts, "from": "0xa", "to": "0xb"}


def _bank(amount, ts=1730000000, ccy="EUR"):
    return {"amount": amount, "currency": ccy, "sent_at": ts, "iban": "DE89"}


def test_three_leg_split_sums_to_bank_amount():
    table = rates.load_rates()
    # 2500 EUR at 0.92 EUR/USDT => ~2717.39 USDT total
    legs = [
        _leg("0xa1", "USDT", 1200.0, 1730000000 + 120),
        _leg("0xa2", "USDT", 800.0,  1730000000 + 400),
        _leg("0xa3", "USDT", 717.39, 1730000000 + 900),
    ]
    out = find_split_candidates(_bank(2500.0), legs, table, window_hours=72)
    assert len(out) == 1
    c = out[0]
    assert c["kind"] == "correlation_candidate"
    assert c["legs"] == 3
    assert len(c["components"]) == 3
    assert c["note"] == ("sum matches; split pattern consistent with mule "
                         "behaviour; not proof of same funds")
    hashes = {x["tx_hash"] for x in c["components"]}
    assert hashes == {"0xa1", "0xa2", "0xa3"}


def test_split_sum_above_tolerance_is_rejected():
    table = rates.load_rates()
    # sum is ~10% above bank amount => outside ±1%
    legs = [
        _leg("0xb1", "USDT", 1500.0, 1730000000 + 60),
        _leg("0xb2", "USDT", 1500.0, 1730000000 + 120),
    ]
    out = find_split_candidates(_bank(2500.0), legs, table, window_hours=72)
    assert out == []


def test_split_with_leg_outside_window_is_rejected():
    table = rates.load_rates()
    legs = [
        _leg("0xc1", "USDT", 1200.0, 1730000000 + 120),
        _leg("0xc2", "USDT", 800.0,  1730000000 + 400),
        # third leg is 100 hours later — outside 72h window
        _leg("0xc3", "USDT", 717.39, 1730000000 + 360_000),
    ]
    out = find_split_candidates(_bank(2500.0), legs, table, window_hours=72)
    assert out == []


def test_six_leg_split_is_not_reported():
    table = rates.load_rates()
    # 6 legs summing exactly to the amount; over the max_legs=5 bound
    legs = [_leg(f"0xd{i}", "USDT", 452.90, 1730000000 + 60 * i)
            for i in range(6)]
    out = find_split_candidates(_bank(2500.0), legs, table, window_hours=72)
    assert out == []


def test_single_leg_is_not_returned_by_split():
    table = rates.load_rates()
    legs = [_leg("0xe1", "USDT", 2717.39, 1730000000 + 60)]
    out = find_split_candidates(_bank(2500.0), legs, table, window_hours=72)
    assert out == []


def test_symbol_without_rate_is_skipped():
    table = rates.load_rates()
    legs = [
        _leg("0xf1", "XYZ", 1200.0, 1730000000 + 60),
        _leg("0xf2", "USDT", 800.0, 1730000000 + 120),
    ]
    # XYZ has no rate; only 1 usable leg => no candidate, no exception
    out = find_split_candidates(_bank(2500.0), legs, table, window_hours=72)
    assert out == []

def test_late_split_is_found_after_sorting():
    """v0.9: a true split that appears late in naive combination order
    must still be found because legs are pre-sorted by EUR proximity."""
    table = rates.load_rates()
    # 40 decoy legs that are each far from 2500/3 EUR, plus 3 true legs
    decoys = [_leg(f"0xdec{i}", "USDT", 10.0, 1730000000 + 60 * (i + 1))
              for i in range(37)]
    true_legs = [
        _leg("0xt1", "USDT", 1200.0, 1730000000 + 120),
        _leg("0xt2", "USDT", 800.0,  1730000000 + 400),
        _leg("0xt3", "USDT", 717.39, 1730000000 + 900),
    ]
    legs = decoys + true_legs
    out = find_split_candidates(_bank(2500.0), legs, table, window_hours=72)
    assert len(out) >= 1
    found = {c["tx_hash"] for c in out[0]["components"]}
    assert found == {"0xt1", "0xt2", "0xt3"}


def test_split_still_bounded_after_sorting():
    """v0.9: sorting does not remove the bound; a wallet with too many
    equally plausible legs still returns at most the bounded set."""
    table = rates.load_rates()
    legs = [_leg(f"0xeq{i}", "USDT", 900.0, 1730000000 + 60 * i)
            for i in range(40)]
    out = find_split_candidates(_bank(2500.0), legs, table, window_hours=72)
    # no set of <=5 legs of 900 USDT sums to ~2717 USDT within +/-1%,
    # so the answer must still be empty
    assert out == []
