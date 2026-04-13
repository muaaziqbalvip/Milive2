import re
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4"
M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"

GROQ_API = os.getenv("GROQ_API")

channels = []

# ======================
# 📥 M3U PARSER
# ======================
def load_m3u():
    global channels
    try:
        res = requests.get(M3U_URL, timeout=20)
        lines = res.text.splitlines()
        channels = []
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
                current = {}
    except Exception as e:
        print(f"Error loading M3U: {e}")

# ======================
# 📺 GRID VIEW (Limited to avoid 413 Error)
# ======================
def build_keyboard(page=0, per_page=40):
    keyboard = []
    row = []
    
    # Sirf specific range ke channels uthayen (e.g. 0 to 40)
    start_index = page * per_page
    end_index = start_index + per_page
    paginated_channels = channels[start_index:end_index]

    for ch in paginated_channels:
        text = f"📺 {ch['name'][:12]}"
        row.append(InlineKeyboardButton(text, url=ch["url"]))

        if len(row) == 4: # 4 Columns
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # Agar mazeed channels hain to "Next" ka button de sakte hain (Optional Logic)
    if len(channels) > end_index:
        keyboard.append([InlineKeyboardButton("Next Page ➡️", callback_data=f"page_{page+1}")])
        
    return InlineKeyboardMarkup(keyboard)

# ======================
# START
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Loading Channels...")
    load_m3u()

    if not channels:
        await update.message.reply_text("❌ No channels found in M3U.")
        return

    await update.message.reply_text(
        "📺 <b>MI TV LIVE BOT</b>\n\n👇 Select Channel (Top 40)",
        parse_mode="HTML",
        reply_markup=build_keyboard(page=0)
    )

# ======================
# 🔍 AI SEARCH (GROQ)
# ======================
def ai_search(query):
    if not GROQ_API:
        return "API Key not found in Environment Variables."
        
    headers = {
        "Authorization": f"Bearer {GROQ_API}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": query}]
    }

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=headers, json=data)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "AI search failed temporarily."

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
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    print("Bot is running...")
    app.run_polling()
