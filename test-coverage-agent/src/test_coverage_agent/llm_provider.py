import os
import requests
from typing import Optional

class LlmProvider:
    """
    Abstract base class for LLM API providers.
    """
    def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement generate_response")


class GeminiProvider(LlmProvider):
    """
    Google Gemini API provider using direct HTTP requests.
    """
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model

    def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        # Use beta endpoint which supports system instruction
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.1
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Failed to parse Gemini response: {data}") from e


class AnthropicProvider(LlmProvider):
    """
    Anthropic Claude API provider using direct HTTP requests.
    """
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.api_key = api_key
        self.model = model

    def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.1,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Failed to parse Anthropic response: {data}") from e


class OpenAiProvider(LlmProvider):
    """
    OpenAI GPT API provider using direct HTTP requests.
    """
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Failed to parse OpenAI response: {data}") from e


def get_llm_provider() -> LlmProvider:
    """
    Factory function that detects API keys in the environment and returns the appropriate provider.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    general_key = os.environ.get("LLM_API_KEY")
    
    # Check general model specification
    model_override = os.environ.get("LLM_MODEL")

    if gemini_key:
        return GeminiProvider(api_key=gemini_key, model=model_override or "gemini-2.5-flash")
    elif anthropic_key:
        return AnthropicProvider(api_key=anthropic_key, model=model_override or "claude-3-5-sonnet-latest")
    elif openai_key:
        return OpenAiProvider(api_key=openai_key, model=model_override or "gpt-4o")
    elif general_key:
        # Fall back to provider defined by LLM_PROVIDER env, defaulting to Gemini
        provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
        if provider == "anthropic":
            return AnthropicProvider(api_key=general_key, model=model_override or "claude-sonnet-4-5-20250929")
        elif provider == "openai":
            return OpenAiProvider(api_key=general_key, model=model_override or "gpt-4o")
        else:
            return GeminiProvider(api_key=general_key, model=model_override or "gemini-2.5-flash")
    else:
        raise ValueError(
            "No LLM API key detected. Please set GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, or LLM_API_KEY."
        )
