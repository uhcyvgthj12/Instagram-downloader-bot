import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

# Telegram Bot Token (Get from @BotFather)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Instagram Credentials (Optional - for private content)
INSTAGRAM = {
    "username": os.getenv("INSTAGRAM_USERNAME", ""),
    "password": os.getenv("INSTAGRAM_PASSWORD", "")
}

# Bot Settings
BOT_SETTINGS = {
    "max_downloads_per_user": 10,  # Downloads per day per user
    "rate_limit": 30,  # Seconds between requests
    "admin_ids": 7912527708,  # Telegram User IDs with admin access
    "allowed_users": []  # Whitelist (empty = public)
}
