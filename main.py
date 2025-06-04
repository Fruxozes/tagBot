import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

TOKEN = os.getenv("TOKEN_BOT_TELEGRAM")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Работаю, хуй не сосу.")

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
        await update.message.reply_text(f"{mention_text}", parse_mode="HTML")
    except Exception as e:
        logging.error("Ошибка при получении администраторов: %s", e)
        await update.message.reply_text("Ошибка при получении информации о пользователях.")


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("all", all))

    app.run_polling()
