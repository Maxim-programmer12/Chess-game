import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ASSESTS_DIR = BASE_DIR / "images"
INIT_POSITIONS = BASE_DIR / "init_positions.json"
DB_FILE = BASE_DIR / "games.db"

def load_bot_token() -> str:
    return os.getenv("TOKEN")