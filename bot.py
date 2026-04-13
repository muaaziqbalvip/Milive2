import re
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"

GROQ_API = os.getenv("GROQ_API")

channels = []

# ======================
# 📥 M3U PARSER
# ======================
def load_m3u():
    global channels
    channels = []

    res = requests.get(M3U_URL, timeout=20)
    lines = res.text.splitlines()

    current = {}

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF"):
            name = re.search(r',(.+)', line)
            logo = re.search(r'tvg-logo="(.+?)"', line)

            current = {
                "name": name.group(1) if name else "Unknown",
                "logo": logo.group(1) if logo else None
            }

        elif line.startswith("http"):
            current["url"] = line
            channels.append(current)

# ======================
# 📺 GRID VIEW (4 COLUMNS)
# ======================
def build_keyboard():
    keyboard = []
    row = []

    for i, ch in enumerate(channels):

        text = f"📺 {ch['name'][:12]}"

        row.append(InlineKeyboardButton(text, url=ch["url"]))

        if len(row) == 4:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

# ======================
# START
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    load_m3u()

    # referral check
    args = context.args
    if args:
        await update.message.reply_text("🔥 Welcome from MI AI Referral System")

    await update.message.reply_text(
        "📺 <b>MI TV LIVE BOT</b>\n\n👇 Select Channel",
        parse_mode="HTML",
        reply_markup=build_keyboard()
    )

# ======================
# 🔍 AI SEARCH (GROQ)
# ======================
def ai_search(query):
    headers = {
        "Authorization": f"Bearer {GROQ_API}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "user", "content": query}
        ]
    }

    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers=headers, json=data)

    return r.json()["choices"][0]["message"]["content"]

# ======================
# MESSAGE HANDLER (SEARCH)
# ======================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.message.text

    if query.startswith("/"):
        return

    result = ai_search(f"Find IPTV channel or answer: {query}")

    await update.message.reply_text(f"🤖 AI:\n{result}")

# ======================
# RUN
# ======================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

app.run_polling()