from robert.agents.base import Agent
from robert import http

class EthplorerAgent(Agent):
    name = "ethplorer"
    chains = ("ethereum",)

    def fetch(self, address, chain):
        if chain != "ethereum":
            raise ValueError("ethplorer: ethereum only")
        url = f"https://api.ethplorer.io/getAddressTransactions/{address}"
        body = http.get(url, params={"apiKey": "freekey", "limit": 50})
        import json
        data = json.loads(body)
        if not isinstance(data, list):
            raise RuntimeError("ethplorer: unexpected payload")
        out = []
        for tx in data:
            out.append({
                "hash": tx.get("hash"),
                "from": tx.get("from"),
                "to": tx.get("to"),
                "value": str(int(float(tx.get("value", 0)) * 10**18)),
                "timeStamp": str(tx.get("timestamp")),
                "chain": chain,
                "source": "ethplorer",
            })
        return out
