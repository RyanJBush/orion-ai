from abc import ABC, abstractmethod


class Tool(ABC):
    name: str

    @abstractmethod
    def run(self, input_text: str) -> str:
        raise NotImplementedError
