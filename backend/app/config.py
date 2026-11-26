import os

from dotenv import load_dotenv

load_dotenv()

KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME")
KAGGLE_KEY = os.getenv("KAGGLE_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
PROVIDER_TIMEOUT = 12.0
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
