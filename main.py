import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes)
import random
import requests
import speech_recognition as sr
import subprocess

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


async def voice_messange_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.voice:
        return

    try:
        voice = msg.voice
        file = await context.bot.get_file(voice.file_id)
        message_id = msg.message_id
        ogg_file = f"voice_{message_id}.ogg"
        wav_file = f"voice_{message_id}.wav"
        await file.download_to_drive(custom_path=ogg_file)
        subprocess.run(["ffmpeg", "-y", "-i", ogg_file, wav_file, ], check=True)
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as sourse:
            audio = recognizer.record(sourse)
        try:
            recognized_text = recognizer.recognize_google(audio, language="ru")
        except sr.UnknownValueError:
            recognizered_text = "Ты еблан? Я не понял, говори внятнее."
        except sr.RequestError as e:
            recognized_text = f"У меня проблемы, хуй тебе а не распознование: {e}"
        await  msg.reply_text(f"Текст голосового:\n{recognized_text}")
    except Exception as e:
        logging.error("Ошибка при обработке голосового сообщения: %s", e)
        await msg.reply_text("Ошибка при обработке голосового сообщения.")
    finally:
        for filename in (ogg_file, wav_file):
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except Exception as ex:
                logging.error("Ошибка удаления файла (какого хуя?) %s: %s:", filename, ex)

async def video_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.video_note:
        return
    video_file = None
    wav_file = None

    try:
        video_note = msg.video_note
        file = await context.bot.get_file(video_note.file_id)
        message_id = msg.message_id
        video_file = f"video_{message_id}.mp4"
        wav_file = f"video_{message_id}.wav"
        await file.download_to_drive(custom_path=video_file)
        subprocess.run([
            "ffmpeg", "-y", "-i", video_file, "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", wav_file],
            check=True
        )
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio = recognizer.record(source)
        try:
            recognized_text = recognizer.recognize_google(audio, language="ru-RU")
        except sr.UnknownValueError:
            recognized_text = "Я не понял, говори внятнее, ебло ты."
        except sr.RequestError as e:
            recognized_text = f"У меня проблемы, хуй тебе а не распознование: {e}"
        await msg.reply_text(f"Распознанный текст кружка:\n{recognized_text}")
    except Exception as e:
        logging.error("Ошибка при обработке кружка: %s", e)
        await msg.reply_text("Ошибка при обработке кружка.")
    finally:
        for fname in (video_file, wav_file):
            if fname and os.path.exists(fname):
                try:
                    os.remove(fname)
                except Exception as ex:
                    logging.error("Ошибка удаления файла (какого хуя?) %s: %s", fname, ex)


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
    app.add_handler(MessageHandler(filters.VOICE, voice_messange_handler))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, video_note_handler))
    app.run_polling()
