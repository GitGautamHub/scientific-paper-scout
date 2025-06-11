import os
from typing import List, Dict, Any, Generator
from openai import OpenAI
# from anthropic import Anthropic 
# import google.generativeai as genai 

from config import LLM_PROVIDER, LLM_MODEL, OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, TOOLS_DEFINITIONS
from utils.logger import print_streaming_response

class LLMClient:
    def __init__(self):
        self.client = self._initialize_client()
        self.model = LLM_MODEL
        self.provider = LLM_PROVIDER

    def _initialize_client(self):
        if LLM_PROVIDER == "openai":
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not found in environment variables.")
            return OpenAI(api_key=OPENAI_API_KEY)
        elif LLM_PROVIDER == "anthropic":
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")
            return Anthropic(api_key=ANTHROPIC_API_KEY)
        elif LLM_PROVIDER == "google":
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY not found in environment variables.")
            genai.configure(api_key=GOOGLE_API_KEY)
            return genai.GenerativeModel(LLM_MODEL)
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

    def generate_response(self, messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        if self.provider == "openai":
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                tool_choice="auto",
                stream=True
            )
            for chunk in stream:
                yield chunk
        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                stream=True
            )
            for chunk in response:
                yield chunk.delta.text if hasattr(chunk.delta, 'text') else ''
            pass 
        elif self.provider == "google":
            response = self.client.generate_content(
                messages,
                tools=TOOLS_DEFINITIONS, 
                stream=True
            )
            for chunk in response:
                yield chunk.text if chunk.text else ''
            pass 
        else:
            raise ValueError(f"Streaming and tool calling not implemented for provider: {self.provider}")