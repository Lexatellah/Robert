import time
import requests
from robert.agents.base import Agent

class BlockscoutAgent(Agent):
    name = "blockscout"
    chains = ("ethereum", "optimism", "gnosis", "polygon", "base",
              "arbitrum", "scroll", "mode", "zksync", "linea")
    BASE = "https://{chain}.blockscout.com/api/v2"
    DOMAIN_OVERRIDES = {"ethereum": "eth"}

    def __init__(self, timeout=30, max_pages=4):
        self.timeout = timeout
        self.max_pages = max_pages

    def fetch(self, address, chain):
        if not self.supports(chain):
            raise ValueError(f"blockscout: unsupported chain {chain}")
        
        host = self.DOMAIN_OVERRIDES.get(chain, chain)
        url = f"https://{host}.blockscout.com/api/v2/addresses/{address}/transactions"
        
        out, params, pages = [], {"items_count": 50}, 0
        while url and pages < self.max_pages:
            r = requests.get(url, params=params, timeout=self.timeout)
            if r.status_code == 403:
                raise RuntimeError("blockscout rate limit (shared pool)")
            r.raise_for_status()
            body = r.json()
            for item in body.get("items", []):
                out.append(self._normalize(item, chain))
            nextp = body.get("next_page_params")
            if not nextp:
                break
            params = nextp
            pages += 1
            time.sleep(0.25)
        return out

    def _normalize(self, item, chain):
        return {
            "hash": item.get("hash"),
            "from": (item.get("from") or {}).get("hash"),
            "to": (item.get("to") or {}).get("hash"),
            "value": str(item.get("value", "0")),
            "timeStamp": str(item.get("timestamp")),
            "chain": chain,
            "source": "blockscout",
        }
