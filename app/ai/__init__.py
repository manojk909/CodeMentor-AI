import os
from app.ai.openai_provider import OpenAIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.claude_provider import ClaudeProvider
from app.ai.local_provider import LocalSampleProvider

def get_ai_provider():
    """Factory function to get the prioritized AI provider based on environment keys"""
    # 1. OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return OpenAIProvider(api_key=openai_key)
        
    # 2. Anthropic Claude
    claude_key = os.environ.get("CLAUDE_API_KEY")
    if claude_key:
        return ClaudeProvider(api_key=claude_key)
        
    # 3. Google Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        return GeminiProvider(api_key=gemini_key)
        
    # 4. OpenRouter (OpenAI-compatible)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        return OpenAIProvider(api_key=openrouter_key, model="deepseek/deepseek-chat:free", base_url="https://openrouter.ai/api/v1")
        
    # 5. DeepSeek (OpenAI-compatible)
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if deepseek_key:
        return OpenAIProvider(api_key=deepseek_key, model="deepseek-chat", base_url="https://api.deepseek.com/v1")
        
    # 6. Fallback
    return LocalSampleProvider()
