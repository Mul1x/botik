import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8674178298:AAFuv0b3fTCANT-ADw3INJtxRKN-WCCLryA")
BOT_USERNAME = os.getenv("BOT_USERNAME", "garantmoskowbot")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7687750743,8072028362").split(",")]
