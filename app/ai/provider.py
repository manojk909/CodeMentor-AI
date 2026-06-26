from abc import ABC, abstractmethod

class BaseAIProvider(ABC):
    @abstractmethod
    def generate_completion(self, prompt: str, response_format: str = "text") -> str:
        """Generate completion from prompt. response_format can be 'text' or 'json'"""
        pass
