# agents/base_agent.py
from langchain.memory import ConversationBufferMemory
from config.database import get_db
from typing import Dict, List, Optional

class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.db = get_db()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    
    def save_chat_history(self, user_message: str, agent_response: str):
        """Save conversation to database"""
        try:
            self.db.table('chat_history').insert({
                'message': user_message,
                'response': agent_response,
                'agent_type': self.name
            }).execute()
        except Exception as e:
            print(f"Error saving chat history: {e}")