import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8455279912:AAFoWu_2-qxq-BoJUjzwXV1tcRcBnBptkhs")
BOT_USERNAME = os.getenv("BOT_USERNAME", "GGuardRobot")
SUPER_ADMIN_IDS = [int(x) for x in os.getenv("SUPER_ADMIN_IDS", "8717189451,8072028362").split(",")]
