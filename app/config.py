import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Set Google environment var globally (optional)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

WP_SITE_URL = os.getenv("WP_SITE_URL")
WP_API_USERNAME = os.getenv("WP_API_USERNAME")
WP_API_APPLICATION_PASSWORD = os.getenv("WP_API_APPLICATION_PASSWORD")
