# config/database.py
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_KEY")
            )
        return cls._instance
    
    def get_client(self):
        return self.client

def get_db():
    """Get database client"""
    return Database().get_client()

def test_connection():
    """Test database connection"""
    try:
        db = get_db()
        result = db.table('organizations').select("count").execute()
        print(f"✅ Database connected")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()