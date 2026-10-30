import time
from robert.agents.blockscout import BlockscoutAgent
from robert.agents.ethplorer import EthplorerAgent
from robert.agents.blockchair import BlockchairAgent
from robert.agents.tokens import TokenTransferAgent
from robert.agents.rpc import RpcAgent

class CircuitBreaker:
    def __init__(self, threshold=3, cooldown=120):
        self.threshold, self.cooldown, self.state = threshold, cooldown, {}
    def allow(self, key):
        s = self.state.get(key)
        if not s: return True
        fails, until = s
        return not (fails >= self.threshold and time.time() < until)
    def record(self, key, ok):
        if ok: self.state.pop(key, None); return
        fails, _ = self.state.get(key, (0, 0))
        self.state[key] = (fails + 1, time.time() + self.cooldown)

class AgentRunner:
    def __init__(self):
        self.tx_agents = [BlockscoutAgent(), EthplorerAgent(), BlockchairAgent()]
        self.token_agents = [TokenTransferAgent()]
        self.breaker = CircuitBreaker()

    def _run(self, agents, address, chain, label):
        txs, errors, seen = [], [], set()
        for agent in agents:
            if not agent.supports(chain): continue
            key = f"{agent.name}:{chain}:{label}"
            if not self.breaker.allow(key):
                errors.append(f"{key}: circuit open"); continue
            try:
                result = agent.fetch(address, chain)
                got = result[0] if isinstance(result, tuple) else result
                self.breaker.record(key, True)
                for tx in got:
                    h = tx.get("hash")
                    if h and (h, tx.get("symbol")) not in seen:
                        seen.add((h, tx.get("symbol")))
                        txs.append(tx)
                print(f"[{agent.name}] {len(got)} {label} on {chain}")
                if got: break
            except Exception as e:
                self.breaker.record(key, False)
                errors.append(f"{key}: {e}")
                print(f"[{agent.name}] failed: {e} - falling back")
        return txs, errors

    def collect(self, address, chain):
        return self._run(self.tx_agents, address, chain, "txs")

    def collect_tokens(self, address, chain):
        return self._run(self.token_agents, address, chain, "token transfers")

RPC = RpcAgent()
