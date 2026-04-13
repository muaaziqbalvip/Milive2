import re
import requests
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# --- CONFIGURATION ---
TOKEN = "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4"
M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"
GROQ_API = os.getenv("GROQ_API") # GitHub Secrets mein lazmi add karen

# Global storage
channels_cache = []

# ======================
# 📥 ADVANCED M3U PARSER
# ======================
def load_m3u():
    global channels_cache
    print("🔄 Parsing M3U and Extracting Logos...")
    try:
        response = requests.get(M3U_URL, timeout=30)
        if response.status_code != 200:
            print("❌ M3U URL not accessible.")
            return

        lines = response.text.splitlines()
        temp_list = []
        current_item = {}

        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                # Extracting Name
                name_match = re.search(r',(.+)', line)
                # Extracting Logo URL
                logo_match = re.search(r'tvg-logo="(.+?)"', line)
                # Extracting Group/Category (Optional)
                group_match = re.search(r'group-title="(.+?)"', line)

                current_item = {
                    "name": name_match.group(1).strip() if name_match else "Unknown Channel",
                    "logo": logo_match.group(1) if logo_match else "https://via.placeholder.com/300?text=No+Logo",
                    "group": group_match.group(1) if group_match else "General"
                }
            elif line.startswith("http"):
                current_item["url"] = line
                temp_list.append(current_item)
                current_item = {}

        channels_cache = temp_list
        print(f"✅ Loaded {len(channels_cache)} channels successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")

# ======================
# 🤖 MI AI (DETAILED IDENTITY)
# ======================
def mi_ai_response(user_text):
    if not GROQ_API:
        return "⚠️ Groq API Key is missing. Please set it in Environment Variables."

    headers = {
        "Authorization": f"Bearer {GROQ_API}",
        "Content-Type": "application/json"
    }

    # Aapki identity set kar di hai
    system_prompt = (
        "Mera naam MI AI hai. Mujhe Muaaz Iqbal ne MiTV Network ke liye banaya hai. "
        "Main MiTV Network ka official AI Assistant hoon. "
        "Muaaz Iqbal ne mujhe isliye banaya hai taake main users ko IPTV channels aur technical help provide kar sakun. "
        "Hamesha user se tameez se baat karo aur Roman Urdu/Hindi mein jawab do. "
        "Agar koi channel ke baare mein puche to use kaho ke channel ka naam likh kar search kare."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.6
    }

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        return res.json()["choices"][0]["message"]["content"]
    except:
        return "Maaf kijiye, abhi mera brain thora thaka hua hai. Dobara koshish karen!"

# ======================
# 🛰️ HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not channels_cache:
        load_m3u()
    
    msg = (
        "👋 **Assalam-o-Alaikum!**\n\n"
        "Main hoon **MI AI**, aapka personal MiTV assistant.\n"
        "Mujhe **Muaaz Iqbal** ne **MiTV Network** ke liye create kiya hai.\n\n"
        "🔹 **Channel Search:** Bas channel ka naam likhen.\n"
        "🔹 **AI Chat:** Mere saath guptagu karen.\n\n"
        "⚡ *Fast & Smooth Streaming!*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    if not user_input or user_input.startswith("/"):
        return

    # 1. Search Logic
    search_results = [ch for ch in channels_cache if user_input.lower() in ch['name'].lower()]

    if search_results:
        # Avoid 413 error: limit to top 10 results
        top_results = search_results[:10]
        
        # Displaying first result with Image/Logo
        first = top_results[0]
        keyboard = []
        
        for ch in top_results:
            keyboard.append([InlineKeyboardButton(f"📺 {ch['name']}", url=ch['url'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        caption = f"🔍 Mujhe `{len(search_results)}` channels mile hain.\n\n📌 **Top Result:** {first['name']}"
        
        try:
            await update.message.reply_photo(
                photo=first['logo'],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except:
            # If photo fails, send text
            await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode="Markdown")
    
    else:
        # 2. AI Logic (if no channel found)
        await update.message.reply_chat_action(ChatAction.TYPING)
        ai_msg = mi_ai_response(user_input)
        await update.message.reply_text(f"🤖 **MI AI:**\n\n{ai_msg}", parse_mode="Markdown")

# ======================
# ⚙️ MAIN RUNNER
# ======================
if __name__ == '__main__':
    # Initial load
    load_m3u()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    
    print("✅ MI AI is now Online and Detailed!")
    app.run_polling()
