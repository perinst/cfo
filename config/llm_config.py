# config/llm_config.py
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

from config.enviroment import get_config

load_dotenv()

# Rebuild model để fix lỗi Pydantic
try:
    from langchain.cache import InMemoryCache

    ChatOpenAI.model_rebuild()
except Exception:
    pass


def get_llm(temperature=0.1):
    """Initialize DeepSeek LLM with OpenAI-compatible API"""
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=get_config("DEEPSEEK_API_KEY"),
        base_url=get_config("DEEPSEEK_BASE_URL"),
        temperature=temperature,
        max_tokens=2000,
    )


def test_connection():
    """Test DeepSeek connection"""
    try:
        llm = get_llm()
        response = llm.invoke("Say 'Connection successful' if you can read this")
        print(f"✅ DeepSeek connected: {response.content}")
        return True
    except Exception as e:
        print(f"❌ DeepSeek connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
