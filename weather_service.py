import requests
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from config import config

logger = logging.getLogger(__name__)

@dataclass
class WeatherInfo:
    temperature: float
    humidity: float
    description: str
    is_outdoor_friendly: bool
    last_updated: datetime = datetime.now()

    def should_refresh(self) -> bool:
        return datetime.now() - self.last_updated > timedelta(minutes=30)

class WeatherServiceError(Exception):
    pass

class WeatherService:
    BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
    cache: dict[str, WeatherInfo] = {}
    
    @classmethod
    def _is_outdoor_friendly(cls, weather_id: int, temp: float) -> bool:
        if temp < 0 or temp > 35:  # Too cold or too hot
            return False
        # Weather condition codes: https://openweathermap.org/weather-conditions
        bad_conditions = range(200, 700)  # Thunderstorm, Drizzle, Rain, Snow
        return weather_id not in bad_conditions
    
    @classmethod
    async def get_weather(cls, city: str) -> Optional[WeatherInfo]:
        try:
            # Check cache first
            if city in cls.cache and not cls.cache[city].should_refresh():
                return cls.cache[city]
            
            params = {
                "q": city,
                "appid": config.WEATHER_API_KEY,
                "units": "metric"
            }
            
            response = requests.get(cls.BASE_URL, params=params)
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Weather API error for {city}: {response.status_code} - {error_text}")
                raise WeatherServiceError(f"API returned status {response.status_code}")
            
            data = response.json()
            weather_info = WeatherInfo(
                temperature=data["main"]["temp"],
                humidity=data["main"]["humidity"],
                description=data["weather"][0]["description"],
                is_outdoor_friendly=cls._is_outdoor_friendly(
                    data["weather"][0]["id"],
                    data["main"]["temp"]
                )
            )
            
            cls.cache[city] = weather_info
            logger.info(f"Successfully fetched weather for {city}: {weather_info.temperature}°C, {weather_info.description}")
            return weather_info
            
        except requests.RequestException as e:
            logger.error(f"Network error fetching weather for {city}: {str(e)}")
            raise WeatherServiceError(f"Network error: {str(e)}")
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse weather data for {city}: {str(e)}")
            raise WeatherServiceError(f"Data parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching weather for {city}: {str(e)}")
            raise WeatherServiceError(f"Unexpected error: {str(e)}")
    
    @classmethod
    def get_workout_adjustment(cls, weather: WeatherInfo) -> tuple[float, str]:
        """Calculate workout intensity adjustment based on weather conditions."""
        if weather.temperature > 30:
            return 0.8, "жаркая погода (снижен расход калорий)"
        elif weather.temperature > 25:
            return 0.9, "тепло (немного снижен расход калорий)"
        elif 15 <= weather.temperature <= 25:
            return 1.0, "комфортная температура"
        elif weather.temperature < 5:
            return 1.2, "прохладно (повышен расход калорий)"
        else:
            return 1.1, "свежо (немного повышен расход калорий)"

weather_service = WeatherService() 