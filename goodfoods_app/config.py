"""
App settings - DB path, LLM endpoint, model params.
"""

DB_PATH = "goodfoods.db"
LLAMA_API_URL = "http://localhost:11434/api/chat"
LLAMA_API_KEY = None
DEFAULT_CITY = "Mumbai"

LLM_MODEL = "llama3.2:3b"
LLM_TEMPERATURE = 0.3
LLM_TOP_P = 0.9
LLM_TIMEOUT = 180
