import os

from dotenv import load_dotenv

load_dotenv()

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "demo")
ALCHEMY_NETWORK = os.getenv("ALCHEMY_NETWORK", "eth-mainnet")

SCORE_MIN = 300
SCORE_MAX = 850

# Linear caps used when normalizing each metric to [0, 1].
AGE_DAYS_CAP = 1825  # 5 years
TX_COUNT_CAP = 500
DEFI_COUNT_CAP = 100

WEIGHT_ACCOUNT_AGE = 0.40
WEIGHT_TX_COUNT = 0.35
WEIGHT_DEFI = 0.25

# Pagination ceiling for Alchemy Transfers API (1000 results per page).
MAX_TRANSFER_PAGES = 4
TRANSFER_PAGE_SIZE = 1000