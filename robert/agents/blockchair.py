from robert.agents.base import Agent
from robert import http
import json

class BlockchairAgent(Agent):
    name = "blockchair"
    chains = ("bitcoin",)

    def fetch(self, address, chain):
        if chain != "bitcoin":
            raise ValueError("blockchair: bitcoin only in v0.4")
        url = f"https://api.blockchair.com/bitcoin/dashboards/address/{address}"
        body = http.get(url, params={"limit": 50, "transaction_details": "true"})
        data = json.loads(body)
        if data.get("context", {}).get("code", 200) != 200:
            raise RuntimeError(f"blockchair: {data.get('context')}")
        entry = data["data"][address]
        addr_info = entry.get("address", {})
        txs = entry.get("transactions", [])
        out = []
        for tx in txs:
            out.append({
                "hash": tx.get("hash"),
                "from": None,
                "to": None,
                "value": str(tx.get("balance_change", 0)),
                "timeStamp": str(tx.get("time")),
                "chain": "bitcoin",
                "source": "blockchair",
                "raw_inputs": tx.get("inputs"),
                "raw_outputs": tx.get("outputs"),
            })
        return out, addr_info
