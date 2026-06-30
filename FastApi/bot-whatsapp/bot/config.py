import os
from dotenv import load_dotenv

load_dotenv()

GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://localhost:3001')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./bot.db')
