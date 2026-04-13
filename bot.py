import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4"

M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"

categories = {}

# =========================
# 📥 M3U PARSER
# =========================
def load_m3u():
    global categories
    categories = {}

    res = requests.get(M3U_URL, timeout=20)
    lines = res.text.splitlines()

    current = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            name = re.search(r',(.+)', line)
            group = re.search(r'group-title="(.+?)"', line)

            current = {
                "name": name.group(1) if name else "Unknown",
                "group": group.group(1) if group else "Other"
            }

        elif line.startswith("http"):
            if current:
                current["url"] = line

                cat = current["group"]

                if cat not in categories:
                    categories[cat] = []

                categories[cat].append(current)

# =========================
# 📺 START MENU
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    load_m3u()

    keyboard = []

    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat|{cat}")
        ])

    await update.message.reply_text(
        "🔥 <b>MI IPTV BOT LIVE</b>\n\n📺 Select Category",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# 📂 CATEGORY HANDLER
# =========================
async def category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, cat = query.data.split("|")

    keyboard = []

    for ch in categories.get(cat, []):
        keyboard.append([
            InlineKeyboardButton(f"📺 {ch['name']}", url=ch["url"])
        ])

    keyboard.append([
        InlineKeyboardButton("⬅️ Back", callback_data="back")
    ])

    await query.edit_message_text(
        f"📂 <b>{cat}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# 🔙 BACK
# =========================
async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []

    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat|{cat}")
        ])

    await query.edit_message_text(
        "📺 <b>Select Category</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# ROUTER
# =========================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data.startswith("cat|"):
        await category(update, context)
    elif query.data == "back":
        await back(update, context)

# =========================
# MAIN
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(router))

app.run_polling(drop_pending_updates=True)