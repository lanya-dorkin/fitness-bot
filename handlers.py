from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import logging
from datetime import datetime

from models import UserProfile, DailyLog, FoodEntry, WorkoutEntry
from config import config
from ai_service import ai_service, AIServiceError
from weather_service import weather_service, WeatherServiceError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

router = Router()
users: dict[int, UserProfile] = {}
daily_logs: dict[int, DailyLog] = {}

def get_main_keyboard(has_profile: bool = False) -> ReplyKeyboardMarkup:
    """Get the main keyboard based on whether user has a profile."""
    buttons = []
    if not has_profile:
        buttons.append([KeyboardButton(text="/start"), KeyboardButton(text="/set_profile")])
    else:
        buttons.extend([
            [KeyboardButton(text="/status"), KeyboardButton(text="/weather")],
            [KeyboardButton(text="/log_water"), KeyboardButton(text="/log_food")],
            [KeyboardButton(text="/log_workout"), KeyboardButton(text="/help")]
        ])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

AVAILABLE_COMMANDS = {
    "start": "👋 Начать работу с ботом",
    "set_profile": "📝 Создать или обновить профиль",
    "status": "📊 Посмотреть текущий прогресс",
    "weather": "🌡 Проверить погоду и рекомендации",
    "log_water": "💧 Записать выпитую воду",
    "log_food": "🍎 Записать съеденную еду",
    "log_workout": "🏃‍♂️ Записать тренировку",
    "help": "❓ Показать справку по командам"
}

class ProfileStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_activity = State()
    waiting_for_city = State()

async def verify_city(city: str) -> bool:
    try:
        await weather_service.get_weather(city)
        return True
    except WeatherServiceError:
        return False

@router.message(CommandStart())
async def cmd_start(message: Message):
    logger.info(f"New user started bot: {message.from_user.id}")
    has_profile = message.from_user.id in users
    
    await message.answer(
        "👋 Привет! Я бот для отслеживания воды, калорий и активности.\n"
        "Используйте /set_profile чтобы начать или /help для справки.",
        reply_markup=get_main_keyboard(has_profile)
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    logger.info(f"User {message.from_user.id} requested help")
    has_profile = message.from_user.id in users
    
    commands_text = "Доступные команды:\n\n" + "\n".join(
        f"/{cmd} - {desc}" for cmd, desc in AVAILABLE_COMMANDS.items()
    )
    
    if not has_profile:
        commands_text += "\n\n⚠️ Создайте профиль с помощью /set_profile чтобы получить доступ ко всем функциям!"
    
    await message.answer(
        commands_text,
        reply_markup=get_main_keyboard(has_profile)
    )

@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} started profile setup")
    await state.set_state(ProfileStates.waiting_for_weight)
    await message.answer(
        "Введите ваш вес (в кг):",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(ProfileStates.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight <= 0 or weight > 300:
            raise ValueError("Weight out of reasonable range")
        logger.info(f"User {message.from_user.id} set weight: {weight}kg")
        await state.update_data(weight=weight)
        await state.set_state(ProfileStates.waiting_for_height)
        await message.answer("Введите ваш рост (в см):")
    except ValueError as e:
        logger.warning(f"Invalid weight input from user {message.from_user.id}: {message.text}")
        await message.answer("Пожалуйста, введите корректный вес (число от 1 до 300).")

@router.message(ProfileStates.waiting_for_height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
        if height <= 0 or height > 250:
            raise ValueError("Height out of reasonable range")
        logger.info(f"User {message.from_user.id} set height: {height}cm")
        await state.update_data(height=height)
        await state.set_state(ProfileStates.waiting_for_age)
        await message.answer("Введите ваш возраст:")
    except ValueError as e:
        logger.warning(f"Invalid height input from user {message.from_user.id}: {message.text}")
        await message.answer("Пожалуйста, введите корректный рост (число от 1 до 250).")

@router.message(ProfileStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0 or age > 120:
            raise ValueError("Age out of reasonable range")
        logger.info(f"User {message.from_user.id} set age: {age}")
        await state.update_data(age=age)
        await state.set_state(ProfileStates.waiting_for_activity)
        await message.answer("Сколько минут активности у вас в день?")
    except ValueError as e:
        logger.warning(f"Invalid age input from user {message.from_user.id}: {message.text}")
        await message.answer("Пожалуйста, введите корректный возраст (число от 1 до 120).")

@router.message(ProfileStates.waiting_for_activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        if activity < 0 or activity > 1440:  # Max minutes in a day
            raise ValueError("Activity minutes out of reasonable range")
        logger.info(f"User {message.from_user.id} set activity: {activity}min/day")
        await state.update_data(activity_minutes=activity)
        await state.set_state(ProfileStates.waiting_for_city)
        await message.answer("В каком городе вы находитесь?")
    except ValueError as e:
        logger.warning(f"Invalid activity input from user {message.from_user.id}: {message.text}")
        await message.answer("Пожалуйста, введите корректное количество минут (от 0 до 1440).")

@router.message(ProfileStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if not await verify_city(city):
        logger.warning(f"Invalid city input from user {message.from_user.id}: {city}")
        await message.answer("Не удалось найти такой город. Пожалуйста, проверьте написание и попробуйте еще раз.")
        return

    data = await state.get_data()
    data["city"] = city
    data["user_id"] = message.from_user.id
    
    users[message.from_user.id] = UserProfile(**data)
    daily_logs[message.from_user.id] = DailyLog(date=datetime.now())
    
    logger.info(f"User {message.from_user.id} completed profile setup with city: {city}")
    
    try:
        weather = await weather_service.get_weather(city)
        await message.answer(
            "✅ Профиль успешно создан!\n\n"
            f"🌡 Текущая погода: {weather.temperature}°C, {weather.description}\n"
            f"💧 Рекомендация по воде: {'Пейте больше воды из-за жаркой погоды!' if weather.temperature > 25 else 'Норма потребления воды обычная.'}\n"
            f"🏃‍♂️ Тренировки на улице: {'рекомендуются' if weather.is_outdoor_friendly else 'не рекомендуются'}\n\n"
            "Используйте кнопки меню или следующие команды:\n"
            "/log_water <мл> - записать выпитую воду\n"
            "/log_food <описание еды> - записать съеденную еду\n"
            "/log_workout <описание> - записать тренировку\n"
            "/status - посмотреть текущий прогресс\n"
            "/weather - проверить погоду и рекомендации\n"
            "/help - показать справку по командам",
            reply_markup=get_main_keyboard(True)
        )
    except WeatherServiceError as e:
        logger.error(f"Weather service error for user {message.from_user.id}: {str(e)}")
        await message.answer(
            "✅ Профиль создан, но возникла проблема с получением погоды.\n"
            "Используйте кнопки меню или команду /help для справки.",
            reply_markup=get_main_keyboard(True)
        )
    finally:
        await state.clear()

@router.message(Command("weather"))
async def cmd_weather(message: Message):
    if not await handle_protected_command(message):
        return
    
    try:
        weather = await weather_service.get_weather(users[message.from_user.id].city)
        intensity_factor, intensity_explanation = weather_service.get_workout_adjustment(weather)
        
        await message.answer(
            f"🌡 Погода в городе {users[message.from_user.id].city}:\n"
            f"  • Температура: {weather.temperature}°C\n"
            f"  • Влажность: {weather.humidity}%\n"
            f"  • Описание: {weather.description}\n\n"
            f"💧 Рекомендация по воде: {'Увеличьте потребление воды!' if weather.temperature > 25 else 'Обычный режим потребления воды.'}\n"
            f"🏃‍♂️ Тренировки на улице: {'рекомендуются' if weather.is_outdoor_friendly else 'не рекомендуются'}\n"
            f"💪 Интенсивность тренировок: {intensity_explanation}",
            reply_markup=get_main_keyboard(True)
        )
    except WeatherServiceError as e:
        logger.error(f"Weather service error for user {message.from_user.id}: {str(e)}")
        await message.answer(
            "Извините, не удалось получить информацию о погоде. Попробуйте позже.",
            reply_markup=get_main_keyboard(True)
        )

@router.message(Command("log_water"))
async def cmd_log_water(message: Message):
    if not await handle_protected_command(message):
        return
        
    try:
        parts = message.text.split()
        if len(parts) == 1:
            # If no amount provided, show help
            await message.answer(
                "Укажите количество воды в миллилитрах после команды.\n"
                "Например: /log_water 250",
                reply_markup=get_main_keyboard(True)
            )
            return
            
        amount = float(parts[1])
        if amount <= 0 or amount > 5000:
            raise ValueError("Water amount out of reasonable range")
            
        user_id = message.from_user.id
        if user_id not in daily_logs:
            daily_logs[user_id] = DailyLog(date=datetime.now())
        
        try:
            weather = await weather_service.get_weather(users[user_id].city)
            daily_logs[user_id].water_intake += amount
            water_norm = users[user_id].calculate_water_norm(weather.temperature)
            
            extra_message = ""
            if weather.temperature > 25:
                extra_message = "\n⚠️ Из-за жаркой погоды рекомендуется пить больше воды!"
            
            logger.info(f"User {user_id} logged water intake: {amount}ml")
            await message.answer(
                f"✅ Записано: {amount}мл воды\n"
                f"💧 Всего за сегодня: {daily_logs[user_id].water_intake}мл\n"
                f"🎯 Дневная норма: {water_norm}мл\n"
                f"📊 Прогресс: {daily_logs[user_id].water_intake/water_norm*100:.1f}%"
                f"{extra_message}",
                reply_markup=get_main_keyboard(True)
            )
        except WeatherServiceError as e:
            logger.error(f"Weather service error for user {user_id}: {str(e)}")
            await message.answer(
                f"✅ Записано: {amount}мл воды\n"
                "❗️ Не удалось получить погоду для расчета нормы воды.",
                reply_markup=get_main_keyboard(True)
            )
    except (ValueError, IndexError) as e:
        logger.warning(f"Invalid water input from user {message.from_user.id}: {message.text}")
        await message.answer(
            "Используйте формат: /log_water <количество в мл> (от 1 до 5000)\n"
            "Например: /log_water 250",
            reply_markup=get_main_keyboard(True)
        )

@router.message(Command("log_food"))
async def cmd_log_food(message: Message):
    try:
        food_description = " ".join(message.text.split()[1:])
        if not food_description:
            raise IndexError("Empty food description")
            
        user_id = message.from_user.id
        if user_id not in users:
            await message.answer("Сначала создайте профиль с помощью /set_profile")
            return
            
        if user_id not in daily_logs:
            daily_logs[user_id] = DailyLog(date=datetime.now())
        
        try:
            calories, explanation = await ai_service.estimate_food_calories(food_description)
            
            food_entry = FoodEntry(
                food_name=food_description,
                calories=calories,
                timestamp=datetime.now(),
                explanation=explanation
            )
            
            daily_logs[user_id].calorie_intake += calories
            daily_logs[user_id].food_log.append(food_entry)
            daily_logs[user_id].update_bmr_calories(users[user_id])
            
            logger.info(f"User {user_id} logged food: {food_description} ({calories}kcal)")
            
            calorie_norm = users[user_id].calculate_calorie_norm()
            await message.answer(
                f"✅ Записано: {food_description}\n"
                f"🍎 Калории: {calories}ккал ({explanation})\n"
                f"📊 Всего калорий за сегодня: {daily_logs[user_id].calorie_intake}ккал\n"
                f"🎯 Дневная норма: {calorie_norm}ккал\n"
                f"⚖️ Баланс: {daily_logs[user_id].calculate_calorie_balance():.1f}ккал"
            )
        except AIServiceError as e:
            logger.error(f"AI service error for user {user_id}: {str(e)}")
            await message.answer(
                "Извините, возникла проблема с оценкой калорийности.\n"
                "Попробуйте описать блюдо более подробно или попробуйте позже."
            )
    except IndexError:
        logger.warning(f"Invalid food input from user {message.from_user.id}: {message.text}")
        await message.answer("Используйте формат: /log_food <описание еды>")

@router.message(Command("log_workout"))
async def cmd_log_workout(message: Message):
    try:
        description = " ".join(message.text.split()[1:])
        if not description:
            raise IndexError("Empty workout description")
        
        user_id = message.from_user.id
        if user_id not in users:
            await message.answer("Сначала создайте профиль с помощью /set_profile")
            return
            
        if user_id not in daily_logs:
            daily_logs[user_id] = DailyLog(date=datetime.now())
        
        try:
            # Parse workout description
            workout_type, minutes, parse_explanation = await ai_service.parse_workout_description(description)
            
            if minutes <= 0 or minutes > 480:  # Max 8 hours
                raise ValueError("Workout duration out of reasonable range")
            
            # Get weather and calculate adjustments
            weather = await weather_service.get_weather(users[user_id].city)
            intensity_factor, intensity_explanation = weather_service.get_workout_adjustment(weather)
            
            # Calculate calories
            calories, explanation = await ai_service.estimate_workout_calories(
                workout_type, minutes, users[user_id].weight
            )
            
            # Adjust calories based on weather
            adjusted_calories = calories * intensity_factor
            
            workout_entry = WorkoutEntry(
                workout_type=workout_type,
                minutes=minutes,
                calories=adjusted_calories,
                timestamp=datetime.now(),
                explanation=f"{explanation} ({intensity_explanation})"
            )
            
            daily_logs[user_id].calorie_burned_exercise += adjusted_calories
            daily_logs[user_id].workout_log.append(workout_entry)
            daily_logs[user_id].update_bmr_calories(users[user_id])
            
            logger.info(f"User {user_id} logged workout: {workout_type} for {minutes}min ({adjusted_calories}kcal)")
            
            outdoor_warning = "" if weather.is_outdoor_friendly else "\n⚠️ Погода не благоприятна для тренировок на улице!"
            duration_note = f" ({parse_explanation})" if "Примерная оценка" in parse_explanation else ""
            
            await message.answer(
                f"✅ Записано: {workout_type} - {minutes}мин{duration_note}\n"
                f"🌡 {intensity_explanation}\n"
                f"🔥 Сожжено калорий: {adjusted_calories:.1f}ккал ({explanation})\n"
                f"💪 Всего сожжено за сегодня:\n"
                f"  • Тренировки: {daily_logs[user_id].calorie_burned_exercise:.1f}ккал\n"
                f"  • Базовый обмен: {daily_logs[user_id].calorie_burned_bmr:.1f}ккал\n"
                f"  • Всего: {daily_logs[user_id].calculate_calorie_burned():.1f}ккал"
                f"{outdoor_warning}"
            )
        except (AIServiceError, WeatherServiceError) as e:
            logger.error(f"Service error for user {user_id}: {str(e)}")
            await message.answer(
                "Извините, возникла проблема с расчетом калорий.\n"
                "Попробуйте еще раз позже."
            )
    except IndexError:
        logger.warning(f"Empty workout description from user {message.from_user.id}")
        await message.answer(
            "Опишите вашу тренировку после команды /log_workout\n"
            "Например:\n"
            "• /log_workout бегал 30 минут\n"
            "• /log_workout плавание час с небольшим\n"
            "• /log_workout побегал от собак минут 10"
        )
    except ValueError as e:
        logger.warning(f"Invalid workout duration from user {message.from_user.id}: {str(e)}")
        await message.answer("Длительность тренировки должна быть от 1 до 480 минут (8 часов).")

@router.message(Command("status"))
async def cmd_status(message: Message):
    if not await handle_protected_command(message):
        return
        
    user_id = message.from_user.id
    if user_id not in daily_logs:
        daily_logs[user_id] = DailyLog(date=datetime.now())
    
    user = users[user_id]
    log = daily_logs[user_id]
    log.update_bmr_calories(user)
    
    try:
        weather = await weather_service.get_weather(user.city)
        water_norm = user.calculate_water_norm(weather.temperature)
        calorie_norm = user.calculate_calorie_norm()
        
        logger.info(f"User {user_id} requested status")
        
        weather_advice = ""
        if weather.temperature > 25:
            weather_advice = "\n⚠️ Из-за жаркой погоды рекомендуется пить больше воды!"
        elif not weather.is_outdoor_friendly:
            weather_advice = "\n⚠️ Погода не благоприятна для тренировок на улице!"
        
        await message.answer(
            f"📊 Ваш прогресс на сегодня:\n\n"
            f"💧 Вода: {log.water_intake}/{water_norm}мл "
            f"({log.water_intake/water_norm*100:.1f}%)\n"
            f"🍎 Потребление калорий: {log.calorie_intake}ккал\n"
            f"🔥 Расход калорий:\n"
            f"  • Тренировки: {log.calorie_burned_exercise:.1f}ккал\n"
            f"  • Базовый обмен: {log.calorie_burned_bmr:.1f}ккал\n"
            f"  • Всего: {log.calculate_calorie_burned():.1f}ккал\n"
            f"⚖️ Баланс калорий: {log.calculate_calorie_balance():.1f}ккал\n"
            f"🌡 Погода: {weather.temperature}°C, {weather.description}"
            f"{weather_advice}",
            reply_markup=get_main_keyboard(True)
        )
    except WeatherServiceError as e:
        logger.error(f"Weather service error for user {user_id}: {str(e)}")
        await message.answer(
            f"📊 Ваш прогресс на сегодня:\n\n"
            f"🍎 Потребление калорий: {log.calorie_intake}ккал\n"
            f"🔥 Расход калорий:\n"
            f"  • Тренировки: {log.calorie_burned_exercise:.1f}ккал\n"
            f"  • Базовый обмен: {log.calorie_burned_bmr:.1f}ккал\n"
            f"  • Всего: {log.calculate_calorie_burned():.1f}ккал\n"
            f"⚠️ Не удалось получить информацию о погоде",
            reply_markup=get_main_keyboard(True)
        )

@router.message(Command(commands=["status", "weather", "log_water", "log_food", "log_workout"]))
async def handle_protected_command(message: Message):
    """Handle commands that require a profile."""
    if message.from_user.id not in users:
        await message.answer(
            "⚠️ Сначала создайте профиль с помощью /set_profile",
            reply_markup=get_main_keyboard(False)
        )
        return False
    return True

@router.message(F.text.startswith('/'))
async def handle_unknown_command(message: Message):
    """Handle unknown commands."""
    command = message.text.split()[0][1:]  # Remove the '/' and get the command name
    if command not in AVAILABLE_COMMANDS:
        has_profile = message.from_user.id in users
        logger.warning(f"User {message.from_user.id} tried unknown command: {command}")
        await message.answer(
            f"❌ Неизвестная команда: /{command}\n"
            "Используйте /help чтобы увидеть список доступных команд.",
            reply_markup=get_main_keyboard(has_profile)
        ) 