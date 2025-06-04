import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes)
import random
import requests

load_dotenv()
TOKEN = os.getenv("TOKEN_BOT_TELEGRAM")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

CITIES = {
    "москва": (55.75, 37.61),
    "санкт-петербург": (59.93, 30.31),
    "братск": (56.15, 101.63),
    "киев": (50.45, 30.52),
    "минск": (53.90, 27.56),
    "новосибирск": (55.03, 82.92)
}


def get_weather(city: str) -> dict:
    city = city.lower().strip()
    if city not in CITIES:
        return {"error": "Город не найден"}
    latitude, longitude = CITIES[city]
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        f"&current_weather=true"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&timezone=auto"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as err:
        logging.error(f"Ошибка запроса: {err}")
        return {"error": "Ошибка запроса"}


def format_weather(data: dict) -> str:
    if "error" in data:
        return data["error"]

    current_weather = ""
    reaction = ""
    if "current_weather" in data:
        temp_now = data["current_weather"]["temperature"]
        wind_now = data["current_weather"]["windspeed"]
        current_weather = (
            f"🌍 <b>Текущая погода:</b>\n"
            f"🌡 Температура: {temp_now}°C\n"
            f"💨 Ветер: {wind_now} м/с\n\n"
        )
        if temp_now >= 25:
            reaction = random.choice(WEATHER_REPLIES["hot"])
        elif temp_now <= 5:
            reaction = random.choice(WEATHER_REPLIES["cold"])
        elif wind_now > 10:
            reaction = random.choice(WEATHER_REPLIES["windy"])
        else:
            reaction = random.choice(WEATHER_REPLIES["normal"])
    else:
        current_weather = "Нет данных о текущей погоде.\n\n"

    forecast_text = ""
    if "daily" in data:
        daily = data["daily"]
        temp_max = daily["temperature_2m_max"][:7]
        temp_min = daily["temperature_2m_min"][:7]
        rain = daily["precipitation_sum"][:7]
        dates = daily["time"][:7]
        forecast_text = "📅 <b>Прогноз на неделю:</b>\n"
        for i in range(7):
            forecast_text += (
                f"{dates[i]}: 🌡 {temp_min[i]}°C - {temp_max[i]}°C, "
                f"☔ Осадки: {rain[i]} мм\n"
            )
    return f"{current_weather}{reaction}\n\n{forecast_text}"


WEATHER_REPLIES = {
    "hot": [
        "Жарковато! Пора доставать плавки и искать ближайший бассейн! 🏖",
        "Солнце жжет! Не забудь защитный крем, чтобы не превратиться в картошку-фри. 🌞",
        "Настоящая духота! Может, лучше спрятаться в холодильнике? ❄️"
    ],
    "cold": [
        "Холодно, как в сердце твоего бывшего! 🧊",
        "Минус на улице, плюс к желанию сидеть дома под пледом! 🥶",
        "Где твой теплый чай и толстый свитер? Сейчас самое время! 🍵"
    ],
    "windy": [
        "Ветер такой, что можно бесплатно испытать эффект парашюта! 💨",
        "Пора привязывать шапку, чтобы она не улетела в другой город! 🎩",
        "Хочешь бесплатную укладку? Просто выйди на улицу! 🌪"
    ],
    "normal": [
        "Погода вроде нормальная! Можно спокойно гулять. 😎",
        "Сегодня идеальный день, чтобы не париться о погоде! 😏",
        "Всё спокойно! Даже синоптики не жалуются. 😆"
    ]
}


async def universal_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        msg = update.channel_post
    if not msg or not msg.text:
        return

    logging.info("Универсальное сообщение: %s", msg.text)
    city = msg.text.lower().strip()
    if city in CITIES:
        weather_data = get_weather(city)
        weather_text = format_weather(weather_data)
        await msg.reply_text(weather_text, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Привет! Отправь название города из следующего списка: " + ", ".join(CITIES.keys()),
        parse_mode="HTML"
    )


async def all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    try:
        admins = await chat.get_administrators()
        mention_list = []
        for admin in admins:
            user = admin.user
            if user.id == context.bot.id:
                continue
            if user.username:
                mention_list.append(f"@{user.username}")
            else:
                mention_list.append(f'<a href="tg://user?id={user.id}">{user.first_name}</a>')
        mention_text = " ".join(mention_list)
        await update.effective_message.reply_text(mention_text, parse_mode="HTML")
    except Exception as e:
        logging.error("Ошибка при получении администраторов: %s", e)
        await update.effective_message.reply_text("Ошибка при получении информации о пользователях.")


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("all", all))
    app.add_handler(MessageHandler(filters.TEXT, universal_message_handler))
    app.run_polling()
