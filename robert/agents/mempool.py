from robert.agents.base import Agent
from robert import http
import json

class MempoolAgent(Agent):
    name = "mempool-space"
    chains = ("bitcoin",)

    BASE = "https://mempool.space/api"

    def fetch(self, address, chain):
        if chain != "bitcoin":
            raise ValueError("mempool-space: bitcoin only")
        body = http.get(f"{self.BASE}/address/{address}/txs")
        txs = json.loads(body)
        if not isinstance(txs, list):
            raise RuntimeError("mempool-space: unexpected payload")
        out = []
        for tx in txs:
            vin = tx.get("vin", [])
            vout = tx.get("vout", [])
            block_time = (tx.get("status") or {}).get("block_time")
            if not block_time:
                continue
            sent_sats = 0
            is_sender = False
            for i in vin:
                prev = i.get("prevout") or {}
                if prev.get("scriptpubkey_address") == address:
                    sent_sats += int(prev.get("value", 0))
                    is_sender = True
            if not is_sender:
                continue
            recipient = None
            for o in vout:
                if o.get("scriptpubkey_address") and o.get("scriptpubkey_address") != address:
                    recipient = o["scriptpubkey_address"]
                    break
            out.append({
                "hash": tx["txid"],
                "from": address,
                "to": recipient,
                "value": str(sent_sats),
                "decimals": 8,
                "symbol": "BTC",
                "timeStamp": int(block_time),
                "chain": "bitcoin",
                "source": self.name,
            })
        return out

