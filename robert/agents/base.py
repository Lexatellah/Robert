from abc import ABC, abstractmethod

class Agent(ABC):
    name: str
    chains: tuple
    @abstractmethod
    def fetch(self, address: str, chain: str):
        ...
    def supports(self, chain: str) -> bool:
        return chain in self.chains
