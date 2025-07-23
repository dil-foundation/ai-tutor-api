import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVEN_VOICE_ID", "mActWQg9kibLro6Z2ouY") 

# General Config
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Database Config - used by database.py for SQLAlchemy
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")


# Wordpress API Credentials
WP_SITE_URL = os.getenv("WP_SITE_URL")
WP_API_USERNAME = os.getenv("WP_API_USERNAME")
WP_USER_NAME = os.getenv("WP_USER_NAME")
WP_API_APPLICATION_PASSWORD = os.getenv("WP_API_APPLICATION_PASSWORD")
WP_USER_PASSWORD = os.getenv("WP_USER_PASSWORD")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
