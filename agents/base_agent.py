# agents/base_agent.py
from config.database import get_db
from config.llm_config import get_llm
from datetime import datetime

class BaseAgent:
    """Base class for all agents"""
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.db = get_db()
        self.llm = get_llm("deepseek")  # or "ollama"
        
    def log_interaction(self, user_id, message, response):
        """Log chat history to database"""
        self.db.table('chat_history').insert({
            'user_id': user_id,
            'message': message,
            'response': response,
            'agent_type': self.name,
            'created_at': datetime.now().isoformat()
        }).execute()