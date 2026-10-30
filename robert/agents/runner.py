import time
from robert.agents.blockscout import BlockscoutAgent
from robert.agents.ethplorer import EthplorerAgent
from robert.agents.rpc import RpcAgent

class CircuitBreaker:
    def __init__(self, threshold=3, cooldown=120):
        self.threshold = threshold
        self.cooldown = cooldown
        self.state = {}

    def allow(self, key):
        s = self.state.get(key)
        if not s:
            return True
        fails, until = s
        if fails >= self.threshold and time.time() < until:
            return False
        return True

    def record(self, key, ok):
        if ok:
            self.state.pop(key, None)
            return
        fails, _ = self.state.get(key, (0, 0))
        self.state[key] = (fails + 1, time.time() + self.cooldown)

class AgentRunner:
    def __init__(self):
        self.agents = [BlockscoutAgent(), EthplorerAgent()]
        self.breaker = CircuitBreaker()

    def collect(self, address, chain):
        txs, errors, seen = [], [], set()
        for agent in self.agents:
            if not agent.supports(chain):
                continue
            key = f"{agent.name}:{chain}"
            if not self.breaker.allow(key):
                errors.append(f"{key}: circuit open")
                continue
            try:
                got = agent.fetch(address, chain)
                self.breaker.record(key, True)
                for tx in got:
                    h = tx.get("hash")
                    if h and h not in seen:
                        seen.add(h)
                        txs.append(tx)
                print(f"[{agent.name}] {len(got)} txs on {chain}")
                if got:
                    break
            except Exception as e:
                self.breaker.record(key, False)
                errors.append(f"{key}: {e}")
                print(f"[{agent.name}] failed: {e} - falling back")
        return txs, errors

RPC = RpcAgent()
