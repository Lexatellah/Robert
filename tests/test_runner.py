import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

def test_runner_registers_each_agent_once():
    from robert.agents.runner import AgentRunner
    r = AgentRunner()
    names = [type(a).__name__ for a in r.tx_agents]
    assert len(names) == len(set(names)), f"duplicate agents: {names}"

def test_mempool_agent_is_registered():
    from robert.agents.runner import AgentRunner
    from robert.agents.mempool import MempoolAgent
    r = AgentRunner()
    assert any(isinstance(a, MempoolAgent) for a in r.tx_agents)
