import os
from dotenv import load_dotenv

# This physically forces Python to read the .env file in your folder
load_dotenv()

# --- Alchemy API Configuration ---
# It will look for ALCHEMY_API_KEY in .env. If it fails, it falls back to "demo"
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "demo")

# --- Scoring Engine Constants ---
SCORE_MIN = 300
SCORE_MAX = 850

WEIGHT_ACCOUNT_AGE = 0.30
WEIGHT_TX_COUNT = 0.30
WEIGHT_DEFI = 0.40

AGE_DAYS_CAP = 1000.0
TX_COUNT_CAP = 500
DEFI_COUNT_CAP = 100

# --- Transfer Fetching Constants ---
MAX_TRANSFER_PAGES = 5
TRANSFER_PAGE_SIZE = 1000