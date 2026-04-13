import re
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4"
M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"
GROQ_API = os.getenv("GROQ_API")

# Global list to store channels for speed
channels_cache = []

# ======================
# 📥 M3U PARSER (Fast Loading)
# ======================
def load_m3u():
    global channels_cache
    print("🔄 Loading M3U Data...")
    try:
        res = requests.get(M3U_URL, timeout=30)
        lines = res.text.splitlines()
        temp_channels = []
        current = {}

        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                name = re.search(r',(.+)', line)
                logo = re.search(r'tvg-logo="(.+?)"', line)
                current = {
                    "name": name.group(1).strip() if name else "Unknown",
                    "logo": logo.group(1) if logo else None
                }
            elif line.startswith("http"):
                current["url"] = line
                temp_channels.append(current)
                current = {}
        
        channels_cache = temp_channels
        print(f"✅ Loaded {len(channels_cache)} channels.")
    except Exception as e:
        print(f"❌ Error loading M3U: {e}")

# ======================
# 🔍 CHANNEL SEARCH LOGIC
# ======================
def search_in_m3u(query):
    query = query.lower()
    results = [ch for ch in channels_cache if query in ch['name'].lower()]
    return results[:20]  # Limit to 20 results to avoid 413 error

# ======================
# 🤖 MI AI (GROQ SYSTEM PROMPT)
# ======================
def ai_chat(user_query):
    if not GROQ_API:
        return "System Error: Groq API Key missing."

    headers = {
        "Authorization": f"Bearer {GROQ_API}",
        "Content-Type": "application/json"
    }

    # Identity Setup
    system_prompt = (
        "Mera naam MI AI hai. Mujhe Muaaz Iqbal ne MiTV Network ke liye banaya hai. "
        "Main ek helpful assistant hoon jo IPTV aur general sawalon ke jawab deta hoon. "
        "Hamesha Urdu ya Roman Urdu mein jawab dene ki koshish karo."
    )

    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    }

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "Maaf kijiye, abhi AI response mein masla aa raha hai."

# ======================
# 🚀 COMMANDS & HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Load channels if list is empty
    if not channels_cache:
        load_m3u()
    
    welcome_msg = (
        "👋 **Assalam-o-Alaikum!**\n\n"
        "Main hoon **MI AI**, aapka MiTV Assistant.\n\n"
        "📺 **Channel Search:** Kisi bhi channel ka naam likhen (e.g., 'ARY' ya 'Sports').\n"
        "🤖 **AI Chat:** Kuch bhi sawal pochen, main jawab doon ga."
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # 1. First, search in Channels
    found_channels = search_in_m3u(text)
    
    if found_channels:
        keyboard = []
        for ch in found_channels:
            keyboard.append([InlineKeyboardButton(f"📺 {ch['name']}", url=ch['url'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"🔍 Mujhe ye {len(found_channels)} channels mile hain:", reply_markup=reply_markup)
    
    else:
        # 2. If no channel found, use Groq AI
        await update.message.reply_chat_action("typing")
        response = ai_chat(text)
        await update.message.reply_text(f"🤖 **MI AI:**\n\n{response}", parse_mode="Markdown")

# ======================
# 🛠️ RUN BOT
# ======================
if __name__ == '__main__':
    # Initial Load
    load_m3u()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 MI TV Bot is Online...")
    app.run_polling()
