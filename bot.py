import os
import re
import json
import random
import asyncio
import logging
import aiohttp
from datetime import datetime
from fuzzywuzzy import process, fuzz
from collections import deque
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

# ==========================================
# ⚙️ 1. CONFIGURATION & CONSTANTS
# ==========================================
TOKEN = "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4"
M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"
GROQ_API = os.getenv("GROQ_API")  # Lazmi Environment variable mein set karen
AI_MODEL = "llama-3.3-70b-versatile"

# Logging setup for debugging (Professional level)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# 🧠 2. GLOBAL DATABASES & MEMORY
# ==========================================
class BotMemory:
    def __init__(self):
        self.channels_cache = []
        self.channel_names = []
        self.active_groups = set()
        # User/Group chat history taake bot context yaad rakhe
        self.chat_history = {} 

bot_db = BotMemory()

# ==========================================
# 🎭 3. GIF & ANIMATION DATABASE
# ==========================================
GIF_LIBRARY = {
    "greeting": [
        "https://media.giphy.com/media/l0FF56cexcW2JAXCJj/giphy.gif",
        "https://media.giphy.com/media/VBTCqsuiYhxUs/giphy.gif"
    ],
    "searching": [
        "https://media.giphy.com/media/26n6WywFabVnj2WzK/giphy.gif",
        "https://media.giphy.com/media/l41lOlmIQyX22EuzO/giphy.gif"
    ],
    "happy": [
        "https://media.giphy.com/media/chzz1FQgqhytWRWbp3/giphy.gif",
        "https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif"
    ],
    "confused": [
        "https://media.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif"
    ]
}

def get_gif(category):
    return random.choice(GIF_LIBRARY.get(category, GIF_LIBRARY["happy"]))

# ==========================================
# 🌐 4. ASYNC NETWORK OPERATIONS (Lag-Free)
# ==========================================
async def fetch_m3u_async():
    """Asynchronously load and parse M3U so the bot never freezes."""
    logger.info("🔄 Downloading M3U from server...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(M3U_URL, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"❌ Failed to fetch M3U. Status: {response.status}")
                    return
                
                text_data = await response.text()
                lines = text_data.splitlines()
                
                temp_list = []
                temp_names = []
                current_item = {}

                for line in lines:
                    line = line.strip()
                    if line.startswith("#EXTINF"):
                        name_match = re.search(r',(.+)', line)
                        logo_match = re.search(r'tvg-logo="(.+?)"', line)
                        group_match = re.search(r'group-title="(.+?)"', line)

                        c_name = name_match.group(1).strip() if name_match else "Unknown Channel"
                        current_item = {
                            "name": c_name,
                            "logo": logo_match.group(1) if logo_match else "https://via.placeholder.com/600x400?text=MiTV+Network",
                            "group": group_match.group(1) if group_match else "General"
                        }
                    elif line.startswith("http"):
                        current_item["url"] = line
                        temp_list.append(current_item)
                        temp_names.append(current_item["name"])
                        current_item = {}

                bot_db.channels_cache = temp_list
                bot_db.channel_names = temp_names
                logger.info(f"✅ Loaded {len(bot_db.channels_cache)} channels perfectly!")
    except Exception as e:
        logger.error(f"❌ Exception in M3U Loader: {e}")

# ==========================================
# 🤖 5. GROQ AI ENGINE (With Memory)
# ==========================================
async def get_ai_response(user_id, user_name, user_text):
    """Llama 3 powered conversation engine with context memory."""
    if not GROQ_API:
        return "⚠️ Groq API Key missing hai dost! Dev ko bolo set kare."

    # Init history
    if user_id not in bot_db.chat_history:
        bot_db.chat_history[user_id] = deque(maxlen=6) # Keeps last 6 messages
    
    bot_db.chat_history[user_id].append({"role": "user", "content": user_text})

    system_prompt = (
        f"Tu MI AI hai, ek intihayi smart, friendly, aur mazahiya assistant. "
        f"Tujhe Muaaz Iqbal ne MiTV Network ke liye banaya hai. Tera user {user_name} hai. "
        "Roman Urdu/Hindi mein dhero baatein kar, dostana mahaul rakh, aur emojis ka bharpoor istemal kar. "
        "Agar user technical baat kare ya ajeeb sawal pooche to smartness aur humor se handle kar. "
        "Hamesha chulbula, zinda-dil aur tezz jawab de!"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(list(bot_db.chat_history[user_id]))

    headers = {"Authorization": f"Bearer {GROQ_API}", "Content-Type": "application/json"}
    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0.8, # Thora creative
        "max_tokens": 1024
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ai_reply = data["choices"][0]["message"]["content"]
                    # Save AI reply to history
                    bot_db.chat_history[user_id].append({"role": "assistant", "content": ai_reply})
                    return ai_reply
                else:
                    return "Yar mera dimaag server se connect nahi ho pa raha. Thori der mein try kar! 🤕"
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Uff! Lagta hai mera network jam gaya hai. Dobara message bhej yar! 😅"

# ==========================================
# 🔍 6. FUZZY MATCHING (Auto Channel Finder)
# ==========================================
def find_channel_smartly(user_text):
    """
    Agar user likhe 'mujhe jio lagado', to ye 'Geo' dhoond nikalega.
    """
    if not bot_db.channel_names:
        return None, None
        
    # Sirf un words pe focus karo jo lambe hon
    words = [w for w in user_text.split() if len(w) > 2]
    best_matches = []

    for word in words:
        # fuzzywuzzy process.extract returns list of tuples (matched_string, score)
        matches = process.extract(word, bot_db.channel_names, limit=3, scorer=fuzz.token_set_ratio)
        for match in matches:
            if match[1] > 80: # 80% se zyada match ho to accept
                best_matches.append(match[0])

    if not best_matches:
        # Check full text as well
        full_match = process.extractOne(user_text, bot_db.channel_names, scorer=fuzz.partial_ratio)
        if full_match and full_match[1] > 85:
            best_matches.append(full_match[0])

    if best_matches:
        # Filter channel objects
        results = [ch for ch in bot_db.channels_cache if ch['name'] in best_matches]
        # Remove duplicates preserving order
        unique_results = {v['name']:v for v in results}.values()
        return True, list(unique_results)
    
    return False, []

# ==========================================
# 🎯 7. BOT HANDLERS & LOGIC
# ==========================================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start message with Welcome GIF"""
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ['group', 'supergroup']:
        bot_db.active_groups.add(chat_id)

    user_name = update.effective_user.first_name
    await update.message.reply_chat_action(ChatAction.UPLOAD_VIDEO) # Fake typing/uploading for realism
    
    welcome_text = (
        f"🌟 **Welcome Yaar {user_name}!** 🌟\n\n"
        "Main hoon **MI AI**, MiTV ka sab se khatarnak aur smart assistant 🤖🔥.\n"
        "Mujhe **Muaaz Iqbal** ne train kiya hai!\n\n"
        "👉 **Kaise Use Karein?**\n"
        "Sirf channel ka naam likh, main khud samajh jaunga aur link nikal donga! Koi /search command ki zaroorat nahi.\n"
        "Aur haan, mere sath gup-shup lagani ho to bas baat shuru kar de! 😎"
    )
    
    await update.message.reply_animation(
        animation=get_gif("greeting"),
        caption=welcome_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def master_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ek akela function jo puri dunya control karega.
    Search bhi yahin, AI Chat bhi yahin. Group logic bhi yahin.
    """
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_name = update.effective_user.first_name
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    # Register group
    if chat_type in ['group', 'supergroup']:
        bot_db.active_groups.add(chat_id)

    is_group = chat_type in ['group', 'supergroup']
    is_reply_to_me = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    am_i_mentioned = f"@{context.bot.username}" in user_text if context.bot.username else False

    # 1. PEHLE CHECK KARO KYA YE CHANNEL MANG RAHA HAI? (Fuzzy Logic)
    found, channels = find_channel_smartly(user_text)

    if found and channels:
        await update.message.reply_chat_action(ChatAction.TYPING)
        
        top_channels = channels[:6] # Display up to 6 channels
        first_chan = top_channels[0]
        
        # Build Grid UI
        keyboard = []
        row = []
        for ch in top_channels:
            row.append(InlineKeyboardButton(f"📺 {ch['name'][:14]}", url=ch['url']))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row: keyboard.append(row)

        caption = (
            f"✨ **Ye le yaar, tera channel mil gaya!**\n\n"
            f"🎯 **Main Match:** {first_chan['name']}\n"
            f"📂 **Category:** {first_chan['group']}\n\n"
            f"👇 Button dabao aur direct dekho!"
        )

        try:
            await update.message.reply_photo(
                photo=first_chan['logo'],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        return # Channel bhej diya, baat khatam.

    # 2. AGAR CHANNEL NAHI HAI, TO KYA CHAT KARNI HAI?
    # Agar group mein hai, to sirf tab bolega jab isko mention kiya ho ya isko reply kiya ho.
    # Agar private me hai, to hamesha bolega.
    if is_group and not (is_reply_to_me or am_i_mentioned):
        return # Ignore random group messages taake bot annoy na kare.

    # Remove bot mention from text to feed clean text to AI
    if context.bot.username:
        clean_text = user_text.replace(f"@{context.bot.username}", "").strip()
    else:
        clean_text = user_text

    await update.message.reply_chat_action(ChatAction.TYPING)
    
    # Get response from AI Memory engine
    ai_reply = await get_ai_response(chat_id if is_group else update.effective_user.id, user_name, clean_text)
    
    # Keyword based emotions for AI replies
    ai_reply_lower = ai_reply.lower()
    if any(word in ai_reply_lower for word in ['khush', 'haha', 'zordar', 'great', 'wow']):
        await update.message.reply_animation(animation=get_gif("happy"))
    
    await update.message.reply_text(ai_reply, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# ⏰ 8. AUTOMATION (Auto-Suggest Engine)
# ==========================================
async def auto_suggest_job(context: ContextTypes.DEFAULT_TYPE):
    """Har 1 ghante mein groups mein premium recommendations."""
    if not bot_db.channels_cache:
        return

    logger.info("⏰ Running Hourly Suggestions...")
    for chat_id in list(bot_db.active_groups):
        try:
            # PTV, Geo, Ten Sports type ke main channels ko weightage dena
            popular_keywords = ["sports", "news", "entertainment", "movie"]
            good_channels = [c for c in bot_db.channels_cache if any(k in c['group'].lower() for k in popular_keywords)]
            
            if good_channels:
                rand_chan = random.choice(good_channels)
            else:
                rand_chan = random.choice(bot_db.channels_cache)

            msg = (
                "🔥 **MiTV hourly Hype!** 🔥\n\n"
                f"Yar kya bore ho rahe ho? Ye lagao aur chill karo:\n"
                f"📺 **{rand_chan['name']}**\n"
                f"🎭 {rand_chan['group']}\n\n"
                "👇 Click karo stream ke liye!"
            )
            kb = [[InlineKeyboardButton("🍿 Stream Now", url=rand_chan['url'])]]
            
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=rand_chan['logo'],
                caption=msg,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Suggestion failed for {chat_id}: {e}")

# ==========================================
# 🚀 9. MAIN EXECUTION (Heart of the Bot)
# ==========================================
async def setup_background_tasks(app):
    """Startup par M3U fetch karta hai taake bot fast rahay."""
    await fetch_m3u_async()
    # Har 3 ghante mein list dobara refresh karega (Dynamic Updates)
    app.job_queue.run_repeating(lambda c: fetch_m3u_async(), interval=10800, first=10800)

def main():
    print("🔥 BOOTING UP MI AI V4.0 (Enterprise Edition) 🔥")
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Job Queue for Auto Suggestions (Interval 3600 sec = 1 hour)
    job_queue = app.job_queue
    job_queue.run_repeating(auto_suggest_job, interval=3600, first=60)

    # Handlers Registration
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, master_message_handler))
    
    # Bot shuru hone se pehle M3U load karwane ka modern tareeqa v20.x me
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fetch_m3u_async())

    print("✅ System Online! AI is breathing. Fuzzy Search Active. Anti-lag Active.")
    
    # Polling start
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
