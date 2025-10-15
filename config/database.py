# config/database.py
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            url = "https://wfoigedwujyibqvdtnjk.supabase.co"
            key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmb2lnZWR3dWp5aWJxdmR0bmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkyMzM1MjAsImV4cCI6MjA3NDgwOTUyMH0.RJSJTq7e51hekJ32QwnTjQZRT8eiEZTMHrZh-5QBIf8"
            cls._instance.client = create_client(url, key)
        return cls._instance
    
    def get_client(self):
        return self.client

# Helper function
def get_db():
    return DatabaseConnection().get_client()