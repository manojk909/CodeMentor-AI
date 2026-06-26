import requests
import json
from app.ai.provider import BaseAIProvider

class ClaudeProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    def generate_completion(self, prompt: str, response_format: str = "text") -> str:
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        data = {
            'model': self.model,
            'max_tokens': 4000,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7
        }
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result['content'][0]['text']
