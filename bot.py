import os
import sys
import signal
import logging
import requests
import telebot
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TELEGRAM_TOKEN or not OPENWEATHER_API_KEY or not CHANNEL_ID:
    raise ValueError("Не заданы переменные окружения. Проверьте секреты в репозитории.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Коломна
LAT = 55.0794
LON = 38.7783


def get_tomorrow_forecast():
    """Запрашивает прогноз на завтра у OpenWeatherMap."""
    # ИСПОЛЬЗУЕМ ЭНДПОИНТ ПРОГНОЗА (5 дней / 3 часа)
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": LAT,
        "lon": LON,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
        "cnt": 16  # 16 * 3 = 48 часов, чтобы точно захватить весь завтрашний день
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        # Определяем дату на "завтра"
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_date = tomorrow.date()

        # Собираем все прогнозы, относящиеся к завтрашнему дню
        tomorrow_items = []
        for item in data.get("list", []):
            item_dt = datetime.fromtimestamp(item["dt"])
            if item_dt.date() == tomorrow_date:
                tomorrow_items.append(item)

        if not tomorrow_items:
            return None

        # Извлекаем температуры (день/ночь) и описания
        temps = [item["main"]["temp"] for item in tomorrow_items]
        day_temp = max(temps)
        night_temp = min(temps)
        # Берём описание из самого "дневного" прогноза (около 12:00)
        # или просто первое доступное
        descriptions = [item["weather"][0]["description"] for item in tomorrow_items]
        # Для простоты берём самое частое описание или первое
        desc = descriptions[len(descriptions)//2] if descriptions else "неизвестно"

        # Ветер и влажность (берём из дневного прогноза)
        wind = tomorrow_items[len(tomorrow_items)//2]["wind"]["speed"]
        humidity = tomorrow_items[len(tomorrow_items)//2]["main"]["humidity"]

        return (
            f"🌤️ Погода в Коломне на завтра ({tomorrow_date.strftime('%d.%m')}):\n"
            f"Днём: {day_temp:.0f}°C, ночью: {night_temp:.0f}°C\n"
            f"Ожидается: {desc.capitalize()}\n"
            f"Ветер: {wind} м/с, влажность: {humidity}%"
        )
    except Exception as e:
        logging.error(f"Ошибка запроса прогноза: {e}")
        return None


def send_to_channel():
    """Публикует прогноз в канал."""
    text = get_tomorrow_forecast()
    if not text:
        logging.error("Не удалось получить прогноз, отправка отменена.")
        return
    try:
        bot.send_message(CHANNEL_ID, text)
        logging.info("Прогноз успешно отправлен в канал.")
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение в канал: {e}")


@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.reply_to(
        message,
        "Привет! Я публикую прогноз погоды по Коломне на завтра каждый день в 10:00 "
        "в канале. Подпишитесь на канал, чтобы получать прогноз."
    )


# Отправляем прогноз сразу при запуске
send_to_channel()

# Даём боту 5 минут на ответы на /start, затем корректно завершаемся
def _shutdown(signum, frame):
    logging.info("Время истекло, завершаем бота.")
    try:
        bot.stop_polling()
    except Exception:
        pass
    sys.exit(0)


signal.signal(signal.SIGALRM, _shutdown)
signal.alarm(5 * 60)

bot.infinity_polling(timeout=30, long_polling_timeout=30)
