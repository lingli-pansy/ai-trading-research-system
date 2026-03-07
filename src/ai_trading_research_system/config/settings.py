from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "dev")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    default_symbol: str = os.getenv("DEFAULT_SYMBOL", "NVDA")
    project_root: Path = Path(__file__).resolve().parents[3]

settings = Settings()
