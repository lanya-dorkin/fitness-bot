# Фитнес-бот для Telegram

Бот поможет следить за водным балансом, питанием и тренировками. Учитывает погоду в вашем городе и автоматически корректирует рекомендации.

## Что умеет бот?

- 💧 Следит за водным балансом с учётом погоды
- 🍎 Считает калории в еде с помощью AI
- 🏃‍♂️ Записывает тренировки и считает сожжённые калории
- 🌡 Даёт рекомендации по тренировкам с учётом погоды
- 📊 Показывает статистику за день

## Как запустить

1. Скачайте код:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Настройте окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

3. Создайте файл `.env` и добавьте ключи:
```
TELEGRAM_API_KEY=ваш_токен_бота
OPENWEATHERMAP_API_KEY=ключ_погоды
DEEPSEEK_API_KEY=ключ_ai
```

4. Запустите бота:
```bash
python bot.py
```

Если используете Docker:
```bash
docker build -t fitness-bot .
docker run --env-file .env fitness-bot
```

## Где взять API ключи

- Токен бота: Напишите [@BotFather](https://t.me/BotFather) в Telegram
- Ключ погоды: Зарегистрируйтесь на [OpenWeatherMap](https://openweathermap.org/api)
- Ключ AI: Получите на [DeepSeek](https://platform.deepseek.com) 