import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import openai
import requests
from googletrans import Translator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# تنظیم توکن تلگرام و کلید OpenAI
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# لیست زبان ها برای انتخاب کاربر
LANGUAGES = {
    "fa": "فارسی",
    "en": "انگلیسی",
    "ar": "عربی",
    # اگه خواستی زبان های دیگه اضافه کن
}

translator = Translator()

user_data = {}

# مرحله 1: استارت و راهنمایی
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! لطفا فایل صوتی یا ویدیویی ارسال کن تا به متن تبدیلش کنم.\n"
        "اول باید زبان فایل صوتی و زبان ترجمه رو انتخاب کنیم."
    )

# مرحله 2: دریافت فایل صوتی یا ویدیو و ذخیره URL
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    if update.message.voice:
        file = await update.message.voice.get_file()
    elif update.message.audio:
        file = await update.message.audio.get_file()
    elif update.message.video:
        file = await update.message.video.get_file()
    elif update.message.document:
        # اگر فایل صوتی بود (بررسی پسوند)
        if update.message.document.mime_type.startswith("audio/") or update.message.document.mime_type.startswith("video/"):
            file = await update.message.document.get_file()

    if not file:
        await update.message.reply_text("فایل صوتی یا ویدیویی معتبر ارسال کن.")
        return

    file_path = await file.download_to_drive()

    chat_id = update.message.chat_id
    user_data[chat_id] = {"file_path": file_path}

    # پرسیدن زبان ورودی
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"input_lang_{code}") for code, name in LANGUAGES.items()]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("زبان فایل صوتی رو انتخاب کن:", reply_markup=reply_markup)

# مرحله 3: انتخاب زبان ورودی
async def input_lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("input_lang_"):
        lang = data.split("_")[-1]
        user_data[chat_id]["input_lang"] = lang

        # پرسیدن زبان خروجی (ترجمه)
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"output_lang_{code}") for code, name in LANGUAGES.items()]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("زبان ترجمه رو انتخاب کن:", reply_markup=reply_markup)

# مرحله 4: انتخاب زبان خروجی
async def output_lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("output_lang_"):
        lang = data.split("_")[-1]
        user_data[chat_id]["output_lang"] = lang

        await query.message.reply_text("در حال پردازش فایل صوتی، لطفا صبر کنید...")

        # تبدیل و ترجمه
        await process_file(chat_id, context)

async def process_file(chat_id, context):
    data = user_data[chat_id]
    file_path = data["file_path"]
    input_lang = data["input_lang"]
    output_lang = data["output_lang"]

    # مرحله تبدیل صدا به متن با Whisper (این قسمت رو ساده گذاشتم، باید مدل واقعی رو جایگزین کنی)
    # فرض می‌کنیم فایل روی دیسک است و با openai.Audio به مدل می‌فرستیم

    with open(file_path, "rb") as audio_file:
        transcription = openai.Audio.transcribe("whisper-1", audio_file, language=input_lang)
        text = transcription["text"]

    # ترجمه متن با googletrans
    if input_lang != output_lang:
        translated = translator.translate(text, src=input_lang, dest=output_lang).text
    else:
        translated = text

    # ارسال متن اصلی و ترجمه
    await context.bot.send_message(chat_id=chat_id, text=f"متن اصلی ({LANGUAGES[input_lang]}):\n{text}\n\nمتن ترجمه‌شده ({LANGUAGES[output_lang]}):\n{translated}")

# راه‌اندازی ربات
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
