import os
import sys
import signal
import logging
import requests
import telebot

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TELEGRAM_TOKEN or not OPENWEATHER_API_KEY or not CHANNEL_ID:
    raise ValueError("Не заданы переменные окружения. Проверьте секреты в репозитории.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

LAT = 55.0794
LON = 38.7783


def get_weather():
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": LAT,
        "lon": LON,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        d = r.json()
        temp = d["main"]["temp"]
        feels = d["main"]["feels_like"]
        hum = d["main"]["humidity"]
        wind = d["wind"]["speed"]
        desc = d["weather"][0]["description"].capitalize()
        return (
            f"🌤️ Погода в Коломне:\n"
            f"Сейчас: {temp:.0f}°C (ощущается как {feels:.0f}°C), {desc}\n"
            f"Ветер: {wind} м/с, влажность: {hum}%"
        )
    except Exception as e:
        logging.error(f"Ошибка запроса погоды: {e}")
        return None


def send_to_channel():
    text = get_weather()
    if not text:
        logging.error("Не удалось получить погоду, отправка отменена.")
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
        "Привет! Я публикую прогноз погоды по Коломне каждый день в 10:00 "
        "в канале. Подпишитесь на канал, чтобы получать прогноз."
    )


send_to_channel()


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
