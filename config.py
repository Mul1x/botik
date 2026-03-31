import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "8616737090:AAHJpZXsAqpiZKqHv2fKfuJ7ALALp-iSRjo")
MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID", "8717189451"))  # ID главного админа

# Путь к видео
VIDEO_PATH = "data/welcome.mp4"

# Состояния разговора
(
    WAITING_DEAL_AMOUNT,
    WAITING_DEAL_DESCRIPTION,
    WAITING_TON_WALLET,
    WAITING_SBP_PHONE,
    WAITING_RF_CARD,
    WAITING_UA_CARD,
    WAITING_ADMIN_USERNAME,
) = range(7)