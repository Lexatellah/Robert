import requests
from robert.agents.base import Agent

class RpcAgent(Agent):
    name = "public-rpc"
    chains = ("ethereum", "arbitrum", "base", "polygon", "optimism")
    ENDPOINTS = {
        "ethereum": ["https://eth.drpc.org", "https://ethereum-rpc.publicnode.com",
                     "https://gateway.tenderly.co/public/mainnet",
                     "https://eth-pokt.nodies.app", "https://eth.meowrpc.com"],
        "arbitrum": ["https://arb1.arbitrum.io/rpc"],
        "base": ["https://mainnet.base.org"],
        "polygon": ["https://polygon-rpc.com"],
        "optimism": ["https://mainnet.optimism.io"],
    }

    def fetch(self, address, chain):
        raise NotImplementedError("use get_transaction / get_balance")

    def _call(self, chain, method, params):
        last = None
        for url in self.ENDPOINTS.get(chain, []):
            try:
                r = requests.post(url, json={"jsonrpc": "2.0", "id": 1,
                                  "method": method, "params": params}, timeout=15)
                r.raise_for_status()
                data = r.json()
                if "result" in data:
                    return data["result"]
                last = data.get("error")
            except Exception as e:
                last = e
        raise RuntimeError(f"all RPC endpoints failed: {last}")

    def get_balance(self, address, chain="ethereum"):
        return int(self._call(chain, "eth_getBalance", [address, "latest"]), 16)

    def get_transaction(self, tx_hash, chain="ethereum"):
        return self._call(chain, "eth_getTransactionByHash", [tx_hash])
