import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

WITHDRAW_GROUP_ID = int(os.getenv("WITHDRAW_GROUP_ID", "0"))
DEPOSIT_GROUP_ID = int(os.getenv("DEPOSIT_GROUP_ID", "0"))

BANNER_IMAGE_URL = os.getenv("BANNER_IMAGE_URL", "")

BKASH_NUMBER = os.getenv("BKASH_NUMBER", "")
NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "")
BINANCE_ID = os.getenv("BINANCE_ID", "")
CRYPTO_ADDRESS = os.getenv("CRYPTO_ADDRESS", "")

MIN_WITHDRAW_BDT = float(os.getenv("MIN_WITHDRAW_BDT", "50"))
WITHDRAW_FEE_PCT = float(os.getenv("WITHDRAW_FEE_PCT", "5"))
USD_RATE_BDT = float(os.getenv("USD_RATE_BDT", "115"))

FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "serviceAccountKey.json")

SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@developer_x_asik_prof")
