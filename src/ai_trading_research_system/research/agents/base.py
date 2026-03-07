from abc import ABC, abstractmethod
from ..schemas import ResearchContext

class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, context: ResearchContext) -> dict:
        raise NotImplementedError
