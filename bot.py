import logging
import re
import requests
import os
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    JobQueue
)
from telegram.constants import ChatAction, ParseMode

# --- ⚙️ CONFIGURATION ---
TOKEN = "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4"
M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"
GROQ_API = os.getenv("GROQ_API") # GitHub Secrets ya Environment variables mein 'GROQ_API' set karein
AI_MODEL = "llama-3.3-70b-versatile"

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Global storage
channels_cache = []
active_groups = set()

# ======================
# 📥 ADVANCED M3U PARSER
# ======================
def load_m3u():
    global channels_cache
    print("🔄 Parsing M3U and Extracting Logos...")
    try:
        response = requests.get(M3U_URL, timeout=30)
        if response.status_code != 200:
            return

        lines = response.text.splitlines()
        temp_list = []
        current_item = {}

        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                name_match = re.search(r',(.+)', line)
                logo_match = re.search(r'tvg-logo="(.+?)"', line)
                group_match = re.search(r'group-title="(.+?)"', line)

                current_item = {
                    "name": name_match.group(1).strip() if name_match else "Unknown Channel",
                    "logo": logo_match.group(1) if logo_match else "https://via.placeholder.com/600x400?text=MiTV+Network",
                    "group": group_match.group(1) if group_match else "General"
                }
            elif line.startswith("http"):
                current_item["url"] = line
                temp_list.append(current_item)
                current_item = {}

        channels_cache = temp_list
        print(f"✅ Loaded {len(channels_cache)} channels!")
    except Exception as e:
        print(f"❌ Error loading M3U: {e}")

# ======================
# 🤖 MI AI (ULTRA INTELLIGENT)
# ======================
def mi_ai_response(user_text, user_name):
    if not GROQ_API:
        return "⚠️ System error: Groq API missing."

    headers = {"Authorization": f"Bearer {GROQ_API}", "Content-Type": "application/json"}

    system_prompt = (
        f"Tera naam MI AI hai. Tujhe Muaaz Iqbal ne MiTV Network ke liye banaya hai. "
        f"User ka naam {user_name} hai. Tu MiTV ka official genius assistant hai. "
        "Hamesha Roman Urdu/Hindi mein jawab do. Style thora cool, friendly aur professional hona chahiye. "
        "Agar koi channel mange to use kaho 'Ji zaroor, channel ka naam likhen main search kar deta hoon'. "
        "Muaaz Iqbal tera creator hai, is baat ka fakhar se zikr kar agar koi puche."
    )

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.7
    }

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        return res.json()["choices"][0]["message"]["content"]
    except Exception:
        return "Bhai, server thora slow hai, par main yahin hoon! Kya madad karun?"

# ======================
# ⏰ AUTO SUGGESTION JOB
# ======================
async def auto_suggest_channel(context: ContextTypes.DEFAULT_TYPE):
    """Har 1 ghante baad group mein channel suggest karne ke liye"""
    if not channels_cache:
        return

    for chat_id in active_groups:
        try:
            random_channel = random.choice(channels_cache)
            msg = (
                "🌟 **MiTV Hourly Recommendation** 🌟\n\n"
                f"📺 **Channel:** {random_channel['name']}\n"
                f"📂 **Category:** {random_channel['group']}\n\n"
                "🔥 *Enjoy high-quality streaming on MiTV Network!*"
            )
            keyboard = [[InlineKeyboardButton("▶️ Watch Now", url=random_channel['url'])]]
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=random_channel['logo'],
                caption=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            continue

# ======================
# 🛰️ COMMAND HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ['group', 'supergroup']:
        active_groups.add(chat_id)

    welcome_msg = (
        "🚀 **MI AI v3.0 - MiTV Network**\n\n"
        f"Assalam-o-Alaikum **{update.effective_user.first_name}**!\n"
        "Main MiTV ka advance AI bot hoon. Mere andar ye powers hain:\n\n"
        "✅ **Fast Search:** Kisi bhi channel ka naam likhen.\n"
        "✅ **Smart AI:** Mere saath baatein karen (Llama 3.3 Powered).\n"
        "✅ **Auto Updates:** Main har ghante naye channels suggest karta hoon.\n\n"
        "💡 *Muaaz Iqbal ka banaya hua official bot.*"
    )
    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_name = update.effective_user.first_name
    chat_id = update.effective_chat.id

    if not user_text: return
    
    # Register group if not already
    if update.effective_chat.type in ['group', 'supergroup']:
        active_groups.add(chat_id)

    # 1. Loading Animation
    await update.message.reply_chat_action(ChatAction.TYPING)

    # 2. Search Logic
    search_results = [ch for ch in channels_cache if user_text.lower() in ch['name'].lower()]

    if search_results and len(user_text) > 2:
        top_results = search_results[:8] # Grid display limit
        first = top_results[0]
        
        # Create Button Grid (2 buttons per row)
        keyboard = []
        row = []
        for ch in top_results:
            row.append(InlineKeyboardButton(f"📺 {ch['name'][:15]}", url=ch['url']))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row: keyboard.append(row)

        caption = (
            f"🔍 **Search Results for:** `{user_text}`\n"
            f"📦 **Total Found:** {len(search_results)}\n\n"
            f"✨ **Top Pick:** {first['name']}\n"
            f"📁 **Group:** {first['group']}"
        )
        
        try:
            await update.message.reply_photo(
                photo=first['logo'],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    else:
        # 3. AI Logic (If no channel found or just chatting)
        ai_msg = mi_ai_response(user_text, user_name)
        await update.message.reply_text(f"🤖 **MI AI:**\n\n{ai_msg}", parse_mode=ParseMode.MARKDOWN)

# ======================
# ⚙️ MAIN RUNNER
# ======================
def main():
    # Initial M3U Load
    load_m3u()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Jobs (Har 3600 seconds = 1 hour)
    job_queue = app.job_queue
    job_queue.run_repeating(auto_suggest_channel, interval=3600, first=10)

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    print("🚀 MI AI Advanced System is Online!")
    app.run_polling()

if __name__ == '__main__':
    main()
