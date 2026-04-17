import os
from dotenv import load_dotenv
from pathlib import Path

# Явно указываем путь к .env в папке bot
env_path = Path('/home/stroitelev91/bot/.env')
load_dotenv(dotenv_path=env_path)

class Config:
    # VK
    VK_TOKEN = os.getenv('VK_TOKEN', '')
    VK_GROUP_ID = int(os.getenv('VK_GROUP_ID', 0))
    VK_CHAT_ID = int(os.getenv('VK_CHAT_ID', 0))

    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # YooKassa
    YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID', '')
    YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY', '')
    YOOKASSA_RETURN_URL_BOT = f"https://vk.me/club{VK_GROUP_ID}" if VK_GROUP_ID else "https://vk.com/"
    YOOKASSA_RETURN_URL_LANDING = "https://mrbodya1.github.io/YUB/thankyou.html"

    # Админы
    ADMINS = [int(x) for x in os.getenv('ADMINS', '').split(',') if x]

config = Config()