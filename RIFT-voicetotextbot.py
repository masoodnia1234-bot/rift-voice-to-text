import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import openai
from googletrans import Translator

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

translator = Translator()

LANGUAGES = {
    "fa": "فارسی",
    "en": "انگلیسی",
    "ar": "عربی",
}

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! لطفا فایل صوتی یا ویدیویی ارسال کن تا به متن تبدیلش کنم.\n"
        "ابتدا زبان فایل و زبان ترجمه را انتخاب کن."
    )

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    if update.message.voice:
        file = await update.message.voice.get_file()
    elif update.message.audio:
        file = await update.message.audio.get_file()
    elif update.message.video:
        file = await update.message.video.get_file()
    elif update.message.document:
        if update.message.document.mime_type.startswith("audio/") or update.message.document.mime_type.startswith("video/"):
            file = await update.message.document.get_file()
    else:
        await update.message.reply_text("فایل صوتی یا ویدیویی معتبر ارسال کن.")
        return

    file_path = await file.download_to_drive()

    chat_id = update.message.chat_id
    user_data[chat_id] = {"file_path": file_path}

    keyboard = [[InlineKeyboardButton(name, callback_data=f"input_lang_{code}") for code, name in LANGUAGES.items()]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("زبان فایل صوتی را انتخاب کن:", reply_markup=reply_markup)

async def input_lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = query.data.split("_")[-1]
    user_data[chat_id]["input_lang"] = lang

    keyboard = [[InlineKeyboardButton(name, callback_data=f"output_lang_{code}") for code, name in LANGUAGES.items()]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("زبان ترجمه را انتخاب کن:", reply_markup=reply_markup)

async def output_lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = query.data.split("_")[-1]
    user_data[chat_id]["output_lang"] = lang

    await query.message.reply_text("در حال پردازش فایل، لطفا صبر کن...")

    await process_file(chat_id, context)

async def process_file(chat_id, context):
    data = user_data[chat_id]
    file_path = data["file_path"]
    input_lang = data["input_lang"]
    output_lang = data["output_lang"]

    with open(file_path, "rb") as audio_file:
        transcription = openai.Audio.transcribe("whisper-1", audio_file, language=input_lang)
        text = transcription["text"]

    if input_lang != output_lang:
        translated = translator.translate(text, src=input_lang, dest=output_lang).text
    else:
        translated = text

    await context.bot.send_message(chat_id=chat_id, text=f"متن اصلی ({LANGUAGES[input_lang]}):\n{text}\n\nمتن ترجمه‌شده ({LANGUAGES[output_lang]}):\n{translated}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO | filters.Document.ALL, handle_audio))
    app.add_handler(CallbackQueryHandler(input_lang_handler, pattern="^input_lang_"))
    app.add_handler(CallbackQueryHandler(output_lang_handler, pattern="^output_lang_"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
