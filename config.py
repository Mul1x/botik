import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8790464708:AAFbSZ9ofxx9H2Ef0O1wX6CGTLVFe7yIIf8")
BOT_USERNAME = os.getenv("BOT_USERNAME", "GGuardRobot")
SUPER_ADMIN_IDS = [int(x) for x in os.getenv("SUPER_ADMIN_IDS", "8717189451,8072028362").split(",")]
