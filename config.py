import os
from dotenv import load_dotenv

load_dotenv() 


# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# MCP Server URLs
PAPER_SEARCH_SERVER_URL = os.getenv("PAPER_SEARCH_SERVER_URL", "http://127.0.0.1:8001")
PDF_SUMMARIZE_SERVER_URL = os.getenv("PDF_SUMMARIZE_SERVER_URL", "http://127.0.0.1:8002")

# Tool Definitions (for LLM function calling)
TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "paper_search",
            "description": "Searches for scientific papers on arXiv based on a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for scientific papers (e.g., 'quantum computing', 'large language models')."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "The maximum number of papers to retrieve.",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pdf_summarize",
            "description": "Summarizes the content of a PDF document given its URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pdf_url": {
                        "type": "string",
                        "description": "The direct URL to the PDF document."
                    }
                },
                "required": ["pdf_url"]
            }
        }
    }
]