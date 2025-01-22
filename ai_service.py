import json
import aiohttp
import logging
import re
from typing import Tuple, Optional
from config import config

logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    pass

class AIService:
    BASE_URL = "https://api.deepseek.com/v1/chat/completions"
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, messages):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.BASE_URL,
                    headers=self.headers,
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 150
                    }
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"AI API error: {response.status} - {error_text}")
                        raise AIServiceError(f"API returned status {response.status}")
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Network error in AI request: {str(e)}")
            raise AIServiceError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in AI request: {str(e)}")
            raise AIServiceError(f"Unexpected error: {str(e)}")
    
    def _extract_json_from_text(self, text: str) -> dict:
        """Extract JSON from text even if it's surrounded by other text."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = text[start:end]
                    return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass
            
            try:
                if "calories" in text.lower() and ("ккал" in text.lower() or "калор" in text.lower()):
                    import re
                    numbers = re.findall(r'\d+(?:\.\d+)?', text)
                    if numbers:
                        return {
                            "calories": float(numbers[0]),
                            "explanation": text.strip()
                        }
            except:
                pass
            
            raise json.JSONDecodeError("Could not extract valid JSON", text, 0)

    def _extract_duration_from_text(self, text: str) -> Optional[float]:
        """Extract duration in minutes from text description."""
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:минут|мин|min)',
            r'(\d+(?:\.\d+)?)\s*(?:час|часа|часов|ч|h)',
            r'(\d+(?:\.\d+)?)\s*(?:сек|секунд|с|s)',
        ]
        
        minutes = 0
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                value = float(match.group(1))
                if 'час' in match.group() or 'h' in match.group():
                    minutes += value * 60
                elif 'мин' in match.group() or 'min' in match.group():
                    minutes += value
                elif 'сек' in match.group() or 's' in match.group():
                    minutes += value / 60
        
        return minutes if minutes > 0 else None
    
    async def parse_workout_description(self, description: str) -> Tuple[str, float, str]:
        """Parse workout type and duration from natural language description."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a fitness expert. Parse workout descriptions and return ONLY a JSON object with this exact format:\n"
                        '{"workout_type": "string", "minutes": number, "explanation": "string"}\n'
                        "If duration is not specified, estimate it based on context. Be conservative in estimates."
                    )
                },
                {
                    "role": "user",
                    "content": f"Parse this workout description: {description}"
                }
            ]
            
            response = await self._make_request(messages)
            content = response["choices"][0]["message"]["content"]
            result = self._extract_json_from_text(content)

            text_duration = self._extract_duration_from_text(description)
            
            workout_type = str(result["workout_type"])
            minutes = float(result.get("minutes", text_duration or 30))
            explanation = str(result.get("explanation", "Оценка на основе описания"))
            
            logger.info(f"Successfully parsed workout: {workout_type} for {minutes} minutes")
            return workout_type, minutes, explanation
            
        except (AIServiceError, json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse workout description: {str(e)}")

            minutes = self._extract_duration_from_text(description) or 30
            return description, minutes, "Примерная оценка длительности"
    
    async def estimate_food_calories(self, food_description: str) -> tuple[float, str]:
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a nutrition expert. Estimate calories for food items and return ONLY a JSON object with this exact format:\n"
                        '{"calories": number, "explanation": "string"}\n'
                        "The calories should be per serving/piece for common items, or per 100g for ingredients.\n"
                        "Be conservative in estimates. Include serving size in explanation."
                    )
                },
                {
                    "role": "user",
                    "content": f"Estimate calories for this food: {food_description}"
                }
            ]
            
            response = await self._make_request(messages)
            try:
                content = response["choices"][0]["message"]["content"]
                result = self._extract_json_from_text(content)
                logger.info(f"Successfully estimated calories for: {food_description}")
                return float(result["calories"]), str(result["explanation"])
            except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
                logger.error(f"Failed to parse AI response for food '{food_description}': {str(e)}\nResponse: {content}")
                messages.append({"role": "assistant", "content": "I'll help estimate calories, but please remind me to respond with valid JSON only."})
                messages.append({"role": "user", "content": f"Please provide calorie estimate for '{food_description}' in EXACT JSON format: {{\"calories\": number, \"explanation\": \"string\"}}"})
                
                try:
                    response = await self._make_request(messages)
                    content = response["choices"][0]["message"]["content"]
                    result = self._extract_json_from_text(content)
                    return float(result["calories"]), str(result["explanation"])
                except:
                    logger.error(f"Second attempt also failed for food '{food_description}'")
                    return 250, f"Примерная оценка для '{food_description}' (ошибка AI)"
        except AIServiceError as e:
            logger.error(f"AI service error for food '{food_description}': {str(e)}")
            return 250, f"Примерная оценка для '{food_description}' (ошибка сервиса)"
    
    async def estimate_workout_calories(self, workout_type: str, minutes: float, weight: float) -> tuple[float, str]:
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a fitness expert. Estimate calories burned during workouts and return ONLY a JSON object with this exact format:\n"
                        '{"calories_per_minute": number, "explanation": "string"}\n'
                        "Consider the person's weight and workout type. Be conservative in estimates."
                    )
                },
                {
                    "role": "user",
                    "content": f"Estimate calories burned per minute for a {workout_type} workout for a person weighing {weight}kg"
                }
            ]
            
            response = await self._make_request(messages)
            try:
                content = response["choices"][0]["message"]["content"]
                result = self._extract_json_from_text(content)
                logger.info(f"Successfully estimated calories for workout: {workout_type}")
                return float(result["calories_per_minute"]) * minutes, str(result["explanation"])
            except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
                logger.error(f"Failed to parse AI response for workout '{workout_type}': {str(e)}\nResponse: {content}")
                met_values = {
                    "ходьба": 3.5,
                    "бег": 8.0,
                    "плавание": 6.0,
                    "велосипед": 7.0,
                    "йога": 2.5,
                    "силовая": 5.0,
                    "бегать": 8.0,
                    "плавать": 6.0,
                    "бегал": 8.0,
                    "плавал": 6.0,
                    "побегал": 8.0,
                    "поплавал": 6.0
                }
                
                # Find closest matching activity
                import difflib
                closest = difflib.get_close_matches(workout_type.lower(), met_values.keys(), n=1, cutoff=0.3)
                met = met_values[closest[0]] if closest else 4.0
                
                calories_per_minute = (met * 3.5 * weight) / 200
                return (calories_per_minute * minutes,
                        f"Оценка на основе MET (metabolic equivalent of task) для '{closest[0] if closest else 'средней активности'}'")
        except AIServiceError as e:
            logger.error(f"AI service error for workout '{workout_type}': {str(e)}")
            return minutes * 7, f"Стандартная оценка расхода калорий (ошибка сервиса)"

ai_service = AIService() 