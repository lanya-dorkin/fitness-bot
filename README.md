# Fitness Tracking Telegram Bot

Telegram бот для отслеживания потребления воды, калорий и физической активности с учетом погодных условий.

## Возможности

- 💧 Отслеживание потребления воды с учетом погоды
- 🍎 Подсчет калорий с помощью AI
- 🏃‍♂️ Учет тренировок с автоматическим расчетом сожженных калорий
- 🌡 Рекомендации по активности на основе погоды
- 📊 Ежедневная статистика и прогресс

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/macOS
# или
.venv\Scripts\activate  # для Windows
pip install -r requirements.txt
```

3. Создайте файл `.env` с необходимыми API ключами:
```
TELEGRAM_API_KEY=your_telegram_bot_token
OPENWEATHERMAP_API_KEY=your_weather_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
```

## Запуск

### Обычный запуск
```bash
python bot.py
```

### Через Docker
```bash
docker build -t fitness-bot .
docker run fitness-bot
```

## API ключи

- Telegram Bot Token: Получите у [@BotFather](https://t.me/BotFather)
- OpenWeatherMap API: [Регистрация](https://openweathermap.org/api)
- DeepSeek API: [Регистрация](https://platform.deepseek.com) 