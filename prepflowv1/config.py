import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'prepflow-secret-2026')
    DATABASE = os.environ.get('DATABASE', 'prepflow.db')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    SESSION_PERMANENT = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024