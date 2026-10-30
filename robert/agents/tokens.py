import time
from robert.agents.base import Agent
from robert import http
import json

class TokenTransferAgent(Agent):
    """ERC-20 transfers for an EVM address, via keyless Blockscout."""
    name = "blockscout-tokens"
    chains = ("ethereum", "optimism", "gnosis", "polygon", "base",
              "arbitrum", "scroll", "mode", "zksync", "linea")
    BASE = "https://{chain}.blockscout.com/api/v2"
    DOMAIN_OVERRIDES = {"ethereum": "eth"}

    def __init__(self, timeout=30, max_pages=4):
        self.timeout = timeout
        self.max_pages = max_pages

    def fetch(self, address, chain):
        if not self.supports(chain):
            raise ValueError(f"tokens: unsupported chain {chain}")
        host = self.DOMAIN_OVERRIDES.get(chain, chain)
        url = (f"https://{host}.blockscout.com/api/v2/addresses/"
               f"{address}/token-transfers?type=ERC-20")
        out, params, pages = [], {"items_count": 50}, 0
        while url and pages < self.max_pages:
            body = json.loads(http.get(url, params=params))
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
        token = item.get("token") or {}
        total = item.get("total") or {}
        return {
            "hash": item.get("transaction_hash"),
            "from": (item.get("from") or {}).get("hash"),
            "to": (item.get("to") or {}).get("hash"),
            "value": str(total.get("value", "0")),
            "decimals": int(token.get("decimals") or total.get("decimals") or 18),
            "symbol": token.get("symbol") or total.get("symbol") or "?",
            "token_address": token.get("address_hash"),
            "timeStamp": item.get("timestamp"),
            "chain": chain,
            "kind": "erc20",
            "source": "blockscout-tokens",
        }
