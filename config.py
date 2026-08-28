import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Пароль для входу в адмін-панель
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Максимальна кількість людей в команді
MAX_TEAM_SIZE = 5

# Час (в хвилинах) на те щоб дістатися до палатки
TIMER_MINUTES = 4

# Шлях до файлу з даними
DATA_FILE = "data/game_data.json"
