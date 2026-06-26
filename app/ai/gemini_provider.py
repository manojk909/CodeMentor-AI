from app.ai.provider import BaseAIProvider

class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model

    def generate_completion(self, prompt: str, response_format: str = "text") -> str:
        from google import genai
        client = genai.Client(api_key=self.api_key)
        
        # If JSON format is requested, we append a strict JSON schema instructions.
        if response_format == "json":
            prompt += "\n\nIMPORTANT: Return ONLY a valid JSON object matching the requested schema. Do not enclose in markdown code blocks."
            
        response = client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        return response.text
