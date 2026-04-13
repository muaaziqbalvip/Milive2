import re
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4"
M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"
# GitHub Secrets ya Environment mein 'GROQ_API' lazmi add karen
GROQ_API = os.getenv("GROQ_API")

channels_cache = []

# ======================
# 📥 M3U & LOGO PARSER
# ======================
def load_m3u():
    global channels_cache
    print("🔄 Loading M3U Data with Logos...")
    try:
        res = requests.get(M3U_URL, timeout=30)
        lines = res.text.splitlines()
        temp_channels = []
        current = {}

        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                # Channel Name and Logo Extraction
                name_match = re.search(r',(.+)', line)
                logo_match = re.search(r'tvg-logo="(.+?)"', line)
                
                current = {
                    "name": name_match.group(1).strip() if name_match else "Unknown Channel",
                    "logo": logo_match.group(1) if logo_match else None
                }
            elif line.startswith("http"):
                current["url"] = line
                temp_channels.append(current)
                current = {}
        
        channels_cache = temp_channels
        print(f"✅ Loaded {len(channels_cache)} channels.")
    except Exception as e:
        print(f"❌ M3U Load Error: {e}")

# ======================
# 🤖 MI AI (GROQ FIX)
# ======================
def ai_chat(user_query):
    if not GROQ_API:
        return "⚠️ Groq API Key nahi mili. Meherbani karke GitHub Secrets check karen."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API}",
        "Content-Type": "application/json"
    }

    system_identity = (
        "Mera naam MI AI hai. Mujhe Muaaz Iqbal ne MiTV Network ke liye banaya hai. "
        "Main MiTV Network ka official AI assistant hoon. Main user ko IPTV channels dhundne "
        "aur technical sawalon mein madad karta hoon. Hamesha Roman Urdu/Hindi mein jawab do."
    )

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_identity},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ AI Error: {response.status_code} - API key ya limit check karen."
    except Exception as e:
        return f"❌ Connection Error: {str(e)}"

# ======================
# 🚀 MESSAGE HANDLER
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    if not query or query.startswith("/"): return

    # 1. Search Channels
    search_query = query.lower()
    matches = [ch for ch in channels_cache if search_query in ch['name'].lower()]

    if matches:
        # 413 Error se bachne ke liye limit (Top 10)
        top_matches = matches[:10]
        keyboard = []
        
        for ch in top_matches:
            keyboard.append([InlineKeyboardButton(f"📺 {ch['name']}", url=ch['url'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Agar exact match ya pehla result logo wala hai to image bhejen
        first_logo = top_matches[0].get('logo')
        
        if first_logo and first_logo.startswith("http"):
            try:
                await update.message.reply_photo(
                    photo=first_logo,
                    caption=f"🔍 Mujhe ye {len(matches)} channels mile hain. Top results niche hain:",
                    reply_markup=reply_markup
                )
                return
            except:
                pass # Agar photo load na ho to simple text bhej dega

        await update.message.reply_text(f"🔍 Mujhe {len(matches)} channels mile hain:", reply_markup=reply_markup)
    
    else:
        # 2. Use AI if no channel found
        await update.message.reply_chat_action("typing")
        ai_response = ai_chat(query)
        await update.message.reply_text(f"🤖 **MI AI:**\n\n{ai_response}", parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not channels_cache: load_m3u()
    welcome = (
        "👋 **Assalam-o-Alaikum!**\n\n"
        "Main hoon **MI AI**, aapka MiTV Assistant.\n"
        "Mujhe **Muaaz Iqbal** ne **MiTV Network** ke liye design kiya hai.\n\n"
        "✨ **Main kya kar sakta hoon?**\n"
        "1️⃣ Kisi bhi channel ka naam likhen (e.g. 'ARY', 'Star').\n"
        "2️⃣ Koi bhi sawal pochen, main AI se jawab doon ga.\n\n"
        "👇 Abhi koi channel search karen!"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

# ======================
# 🛠️ RUN
# ======================
if __name__ == '__main__':
    load_m3u()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 MI AI Bot is active...")
    app.run_polling()
