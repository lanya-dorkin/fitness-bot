from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN: str = getenv("TELEGRAM_API_KEY")
    WEATHER_API_KEY: str = getenv("OPENWEATHERMAP_API_KEY")
    DEEPSEEK_API_KEY: str = getenv("DEEPSEEK_API_KEY")

config = Config() 