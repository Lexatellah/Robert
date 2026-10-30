import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import json
from unittest.mock import patch
from robert.agents.mempool import MempoolAgent

FIXTURE = [
    {
        "txid": "abc123",
        "status": {"block_time": 1730000000, "confirmed": True},
        "vin": [
            {"prevout": {"scriptpubkey_address": "bc1qtest", "value": 50000}},
        ],
        "vout": [
            {"scriptpubkey_address": "bc1qother", "value": 49000},
        ],
    },
]


def test_mempool_normalizes_outgoing_tx():
    with patch("robert.agents.mempool.http.get",
               return_value=json.dumps(FIXTURE).encode()):
        out = MempoolAgent().fetch("bc1qtest", "bitcoin")
    assert len(out) == 1
    r = out[0]
    assert r["hash"] == "abc123"
    assert r["from"] == "bc1qtest"
    assert r["to"] == "bc1qother"
    assert r["value"] == "50000"
    assert r["decimals"] == 8
    assert r["symbol"] == "BTC"
    assert r["timeStamp"] == 1730000000
    assert r["chain"] == "bitcoin"
    assert r["source"] == "mempool-space"


def test_mempool_rejects_unsupported_chain():
    import pytest
    with pytest.raises(ValueError):
        MempoolAgent().fetch("x", "ethereum")
