import re
import requests
import os
import asyncio
import random
import time
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, ChatMemberAdministrator, ChatMemberOwner
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler,
    filters, ContextTypes
)
from telegram.constants import ChatAction
from telegram.error import TelegramError

# =====================================================
# ⚙️ CONFIGURATION
# =====================================================
TOKEN        = os.getenv("BOT_TOKEN", "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4")
M3U_URL      = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"
GROQ_API     = os.getenv("GROQ_API")
WEBSITE_URL  = "https://mitvnet.vercel.app"
BOT_USERNAME = "muslimislamaibot"
BOT_LINK     = f"https://t.me/{BOT_USERNAME}?start=_tgr_FR4NUXM0ODc8"

# ---- COLOR PALETTE for buttons (random per response) ----
# Telegram doesn't support colored buttons natively,
# but we use emoji circles to simulate color feel.
COLOR_EMOJIS = ["🔴","🟠","🟡","🟢","🔵","🟣","🟤","⚫","⚪","🩵","🩷","🩶"]

# ---- Players / Apps ----
PLAYERS = {
    "NS Player":  "https://play.google.com/store/apps/details?id=com.nsp.nsplayer",
    "MX Player":  "https://play.google.com/store/apps/details?id=com.mxtech.videoplayer.ad",
    "VLC":        "https://play.google.com/store/apps/details?id=org.videolan.vlc",
    "TiviMate":   "https://play.google.com/store/apps/details?id=ar.tvplayer.tv",
    "IPTV Smarters": "https://play.google.com/store/apps/details?id=com.nativesoft.iptvpro",
    "Perfect Player": "https://play.google.com/store/apps/details?id=ru.iptvremote.android.iptv",
}

# ---- Free M3U Sources ----
FREE_M3U_LINKS = [
    {"name": "IPTV-org Global",  "url": "https://iptv-org.github.io/iptv/index.m3u"},
    {"name": "IPTV-org Pakistan","url": "https://iptv-org.github.io/iptv/countries/pk.m3u"},
    {"name": "IPTV-org Sports",  "url": "https://iptv-org.github.io/iptv/categories/sports.m3u"},
    {"name": "IPTV-org News",    "url": "https://iptv-org.github.io/iptv/categories/news.m3u"},
    {"name": "IPTV-org Kids",    "url": "https://iptv-org.github.io/iptv/categories/kids.m3u"},
    {"name": "MiTV Playlist",    "url": M3U_URL},
]

# ---- Allowed Users (whitelist for M3U link access) ----
# Empty = open to all verified members
WHITELIST_USERS = set()

# =====================================================
# 🗃️ GLOBAL STATE
# =====================================================
channels_cache: list = []
last_load_time: float = 0
CACHE_TTL = 3600  # Reload M3U every 1 hour

# =====================================================
# 🎨 HELPERS
# =====================================================
def rand_color():
    return random.choice(COLOR_EMOJIS)

def rand_color_batch(n):
    return [random.choice(COLOR_EMOJIS) for _ in range(n)]

def loading_bar(current, total, length=10):
    filled = int(length * current / total)
    return "▓" * filled + "░" * (length - filled)

# =====================================================
# 📥 ADVANCED M3U PARSER  (with auto-refresh)
# =====================================================
def load_m3u(force=False):
    global channels_cache, last_load_time
    now = time.time()
    if not force and channels_cache and (now - last_load_time) < CACHE_TTL:
        return  # Still fresh

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
                name_match  = re.search(r',(.+)',              line)
                logo_match  = re.search(r'tvg-logo="(.+?)"',   line)
                group_match = re.search(r'group-title="(.+?)"', line)
                id_match    = re.search(r'tvg-id="(.+?)"',      line)
                current_item = {
                    "name":  name_match.group(1).strip()  if name_match  else "Unknown Channel",
                    "logo":  logo_match.group(1)           if logo_match  else "",
                    "group": group_match.group(1)          if group_match else "General",
                    "id":    id_match.group(1)             if id_match    else "",
                }
            elif line.startswith("http"):
                current_item["url"] = line
                temp_list.append(current_item)
                current_item = {}

        channels_cache = temp_list
        last_load_time = now
        print(f"✅ Loaded {len(channels_cache)} channels successfully!")
    except Exception as e:
        print(f"❌ Error loading M3U: {e}")

def get_categories():
    cats = {}
    for ch in channels_cache:
        g = ch.get("group", "General")
        cats[g] = cats.get(g, 0) + 1
    return dict(sorted(cats.items(), key=lambda x: -x[1]))

# =====================================================
# 🤖 MI AI  — Groq LLM
# =====================================================
def mi_ai_response(user_text: str, history: list = None) -> str:
    if not GROQ_API:
        return (
            "⚠️ *MI AI abhi available nahi hai.*\n\n"
            "Developer se rabta karen:\n"
            f"🌐 {WEBSITE_URL}"
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API}",
        "Content-Type":  "application/json"
    }

    system_prompt = (
        "Tera naam **MI AI** hai. Tu **Muaaz Iqbal** ka banaya hua AI assistant hai.\n"
        "Tu **MiTV Network** (mitvnet.vercel.app) ka official assistant hai.\n\n"
        "Teri specializations:\n"
        "- IPTV channels dhundhna aur recommend karna\n"
        "- NS Player, MX Player, VLC, TiviMate, IPTV Smarters mein channels kaise chalayein\n"
        "- M3U playlist help\n"
        "- Islamic content, channels aur resources recommend karna\n"
        "- General knowledge aur friendly conversation\n\n"
        "Rules:\n"
        "- Hamesha Roman Urdu mein jawab do unless user English mein pooche\n"
        "- Khud ko MI AI batao, ChatGPT ya koi aur AI nahi\n"
        "- Tameezdar, dost aur helpful raho\n"
        "- Emojis ka use karo lekin zyada nahi\n"
        "- Channel search ke liye user ko guide karo\n"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-10:])  # Last 10 turns for context
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    messages,
        "temperature": 0.65,
        "max_tokens":  800,
    }

    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=20
        )
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"🤖 Maaf kijiye, abhi thoda issue hai. Dobara try karen!\n_{e}_"

# =====================================================
# 🔑 MEMBERSHIP CHECK
# =====================================================
async def is_member_of_bot(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check karta hai ke user ne bot start kiya hua hai ya nahi."""
    # Telegram mein direct check nahi hota, isliye
    # hum user ko simply bot start karne ka kahenge.
    return True  # Open access — restrict karna ho to yahan logic add karo

# =====================================================
# 🎬 ANIMATED START  — with typewriter-style sections
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_m3u()
    user = update.effective_user
    name = user.first_name or "Dost"

    # Check if added to group/channel
    chat_type = update.effective_chat.type

    welcome_text = (
        f"✨ *Assalam-o-Alaikum, {name}!* ✨\n\n"
        f"🤖 Main hoon *MI AI* — Muaaz Iqbal ka banaya hua\n"
        f"🛰️ *MiTV Network* ka official IPTV + AI Assistant!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 *{len(channels_cache):,}* Channels Available\n"
        f"🌐 Website: {WEBSITE_URL}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 *Neeche se koi bhi option chunen:*"
    )

    keyboard = build_main_menu()
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

def build_main_menu():
    colors = rand_color_batch(10)
    buttons = [
        [
            InlineKeyboardButton(f"{colors[0]} 📺 Channel Search",  callback_data="menu_search"),
            InlineKeyboardButton(f"{colors[1]} 🗂️ Categories",      callback_data="menu_categories"),
        ],
        [
            InlineKeyboardButton(f"{colors[2]} 🆓 Free M3U Links",  callback_data="menu_m3u"),
            InlineKeyboardButton(f"{colors[3]} 📱 IPTV Players",    callback_data="menu_players"),
        ],
        [
            InlineKeyboardButton(f"{colors[4]} 🤖 AI Chat",         callback_data="menu_ai"),
            InlineKeyboardButton(f"{colors[5]} ℹ️ MiTV Info",       callback_data="menu_info"),
        ],
        [
            InlineKeyboardButton(f"{colors[6]} 🌐 Website",         url=WEBSITE_URL),
            InlineKeyboardButton(f"{colors[7]} 📲 Share Bot",       url=f"https://t.me/share/url?url={BOT_LINK}&text=MiTV+AI+Bot+–+Best+IPTV+Assistant!"),
        ],
        [
            InlineKeyboardButton(f"{colors[8]} 🔄 Reload Channels", callback_data="menu_reload"),
            InlineKeyboardButton(f"{colors[9]} ❓ Help",            callback_data="menu_help"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)

# =====================================================
# 📞 CALLBACK QUERY HANDLER  — all button presses
# =====================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ---- Main Menu sections ----
    if data == "menu_search":
        await query.edit_message_text(
            "🔍 *Channel Search*\n\n"
            "Bas channel ka naam type karein!\n\n"
            "Misal ke taur par:\n"
            "`ARY News`\n`Geo TV`\n`PTV Sports`\n`Discovery`\n`CNN`\n\n"
            "Main automatically search karunga aur logo ke saath result dunga! 📺",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="menu_back")
            ]])
        )

    elif data == "menu_categories":
        cats = get_categories()
        if not cats:
            await query.edit_message_text("⚠️ Channels load nahi huay. /reload try karen.")
            return
        text = "🗂️ *Channel Categories*\n\n"
        colors = rand_color_batch(len(cats))
        btns = []
        for i, (cat, count) in enumerate(list(cats.items())[:24]):
            btns.append(InlineKeyboardButton(
                f"{colors[i]} {cat} ({count})",
                callback_data=f"cat_{cat[:30]}"
            ))
        # Group into 2 columns
        keyboard = [btns[i:i+2] for i in range(0, len(btns), 2)]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
        await query.edit_message_text(
            text + f"Total: *{len(channels_cache):,}* channels",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("cat_"):
        cat_name = data[4:]
        results = [ch for ch in channels_cache if ch.get("group","").startswith(cat_name)]
        await send_channel_list(query, results[:15], f"📂 {cat_name}", show_back="menu_categories")

    elif data == "menu_m3u":
        colors = rand_color_batch(len(FREE_M3U_LINKS))
        btns = []
        for i, m3u in enumerate(FREE_M3U_LINKS):
            btns.append([InlineKeyboardButton(
                f"{colors[i]} {m3u['name']}",
                url=m3u['url']
            )])
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
        await query.edit_message_text(
            "🆓 *Free M3U Playlist Links*\n\n"
            "⚠️ *Note:* Yeh links use karne ke liye pehle *MI AI Bot* start karen:\n"
            f"👉 [Bot Link]({BOT_LINK})\n\n"
            "Apni pasand ki playlist choose karen:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns),
            disable_web_page_preview=True
        )

    elif data == "menu_players":
        colors = rand_color_batch(len(PLAYERS))
        btns = []
        for i, (name, url) in enumerate(PLAYERS.items()):
            btns.append([InlineKeyboardButton(f"{colors[i]} {name}", url=url)])
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
        await query.edit_message_text(
            "📱 *IPTV Players — Recommended*\n\n"
            "Inhe install karen aur M3U link daalen:\n\n"
            "🏆 *Best for IPTV:* NS Player / TiviMate\n"
            "🎬 *Best for Videos:* MX Player / VLC\n"
            "🌟 *All-in-one:* IPTV Smarters Pro\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

    elif data == "menu_ai":
        await query.edit_message_text(
            "🤖 *MI AI — Chat Mode*\n\n"
            "Ab seedha apna sawaal type karen!\n\n"
            "Main in topics mein help kar sakta hoon:\n"
            "• 📺 IPTV channels aur playlists\n"
            "• 📱 Player setup (NS, MX, VLC, TiviMate)\n"
            "• 🕌 Islamic channels aur content\n"
            "• 💬 General knowledge\n"
            "• 🛠️ Technical IPTV issues\n\n"
            "_Kuch bhi puchein — main hamesha haazir hoon!_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="menu_back")
            ]])
        )

    elif data == "menu_info":
        cats = get_categories()
        top_cats = list(cats.items())[:5]
        top_str = "\n".join([f"  • {c}: {n} channels" for c, n in top_cats])
        await query.edit_message_text(
            f"ℹ️ *MiTV Network — Info*\n\n"
            f"🌐 Website: {WEBSITE_URL}\n"
            f"🤖 Bot: @{BOT_USERNAME}\n"
            f"👨‍💻 Developer: Muaaz Iqbal\n\n"
            f"📊 *Channel Stats:*\n"
            f"  📺 Total: *{len(channels_cache):,}* channels\n"
            f"  🗂️ Categories: *{len(cats)}*\n\n"
            f"🏆 *Top Categories:*\n{top_str}\n\n"
            f"📅 Last Updated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Visit Website", url=WEBSITE_URL)],
                [InlineKeyboardButton("🔙 Back",          callback_data="menu_back")]
            ])
        )

    elif data == "menu_reload":
        await query.edit_message_text("🔄 *Channels reload ho rahay hain...*", parse_mode="Markdown")
        load_m3u(force=True)
        await query.edit_message_text(
            f"✅ *Reload Complete!*\n\n"
            f"📺 Total Channels: *{len(channels_cache):,}*\n"
            f"⏰ Updated: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")
            ]])
        )

    elif data == "menu_help":
        await query.edit_message_text(
            "❓ *Help & Guide*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔍 *Channel Search:*\n"
            "  Seedha channel ka naam likhen\n"
            "  Misal: `ARY`, `Geo`, `Star Plus`\n\n"
            "📱 *IPTV Players:*\n"
            "  NS Player best hai IPTV ke liye\n"
            "  M3U link copy karke player mein daalein\n\n"
            "🆓 *Free M3U:*\n"
            "  Pehle bot start karen, phir link use karen\n\n"
            "🤖 *AI Chat:*\n"
            "  Koi bhi sawaal puchein Roman Urdu mein\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📞 *Support:*\n"
            f"  🌐 {WEBSITE_URL}\n"
            f"  🤖 @{BOT_USERNAME}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Support Website", url=WEBSITE_URL)],
                [InlineKeyboardButton("🔙 Back",            callback_data="menu_back")]
            ])
        )

    elif data == "menu_back":
        load_m3u()
        user = update.effective_user
        name = user.first_name or "Dost"
        welcome_text = (
            f"✨ *Assalam-o-Alaikum, {name}!* ✨\n\n"
            f"🤖 Main hoon *MI AI* — MiTV Network ka IPTV + AI Assistant!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📺 *{len(channels_cache):,}* Channels Available\n"
            f"🌐 {WEBSITE_URL}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👇 *Neeche se koi bhi option chunen:*"
        )
        await query.edit_message_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=build_main_menu(),
            disable_web_page_preview=True
        )

    # ---- Channel detail ----
    elif data.startswith("ch_detail_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(channels_cache):
            ch = channels_cache[idx]
            await send_channel_detail(query, ch, idx)

    elif data.startswith("ch_page_"):
        # Pagination: ch_page_{query}_{page}
        parts = data.split("_", 3)
        page     = int(parts[2])
        q        = parts[3] if len(parts) > 3 else ""
        results  = [ch for ch in channels_cache if q.lower() in ch["name"].lower()]
        await send_channel_list(query, results, f"🔍 '{q}'", page=page, query_str=q)

# =====================================================
# 📺 CHANNEL DISPLAY HELPERS
# =====================================================
async def send_channel_list(query_or_msg, results, title, page=0, query_str="", show_back="menu_back"):
    per_page = 10
    total    = len(results)
    start_i  = page * per_page
    end_i    = start_i + per_page
    page_results = results[start_i:end_i]

    if not page_results:
        text = f"😕 *{title}*\n\nKoi channel nahi mila."
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=show_back)]]
        if hasattr(query_or_msg, 'edit_message_text'):
            await query_or_msg.edit_message_text(text, parse_mode="Markdown",
                                                  reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query_or_msg.reply_text(text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
        return

    colors = rand_color_batch(len(page_results))
    text = (
        f"📺 *{title}*\n"
        f"Mila: *{total}* channels  {loading_bar(min(end_i,total), total)} {min(end_i,total)}/{total}\n\n"
        f"Kisi channel par click karen detail ke liye:"
    )

    btns = []
    for i, ch in enumerate(page_results):
        global_idx = start_i + i
        btns.append([InlineKeyboardButton(
            f"{colors[i]} {ch['name']}",
            callback_data=f"ch_detail_{global_idx}"
        )])

    # Pagination row
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"ch_page_{page-1}_{query_str}"))
    if end_i < total:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"ch_page_{page+1}_{query_str}"))
    if nav:
        btns.append(nav)

    btns.append([InlineKeyboardButton("🔙 Back", callback_data=show_back)])
    kb = InlineKeyboardMarkup(btns)

    if hasattr(query_or_msg, 'edit_message_text'):
        await query_or_msg.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await query_or_msg.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def send_channel_detail(query, ch: dict, idx: int):
    name  = ch.get("name",  "Unknown")
    logo  = ch.get("logo",  "")
    group = ch.get("group", "General")
    url   = ch.get("url",   "")

    # Player deep-links (m3u stream)
    ns_link  = f"nsvideo://{url}"
    vlc_link = f"vlc://{url}"

    detail_text = (
        f"📺 *{name}*\n\n"
        f"🗂️ Category: `{group}`\n"
        f"🔗 Stream: Available\n\n"
        f"▶️ *Kisi bhi player mein chalayein:*"
    )

    c = rand_color_batch(6)
    btns = [
        [
            InlineKeyboardButton(f"{c[0]} ▶️ Direct Link",    url=url),
            InlineKeyboardButton(f"{c[1]} 📋 Copy URL",       callback_data=f"copy_{idx}"),
        ],
        [
            InlineKeyboardButton(f"{c[2]} 🎬 Open in VLC",   url=vlc_link),
            InlineKeyboardButton(f"{c[3]} 📺 NS Player",     url=ns_link),
        ],
        [
            InlineKeyboardButton(f"{c[4]} 🌐 MiTV Website",  url=WEBSITE_URL),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_back")],
    ]

    try:
        if logo and logo.startswith("http"):
            await query.edit_message_media(
                media=__import__('telegram').InputMediaPhoto(
                    media=logo, caption=detail_text, parse_mode="Markdown"
                ),
                reply_markup=InlineKeyboardMarkup(btns)
            )
        else:
            await query.edit_message_text(
                detail_text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(btns)
            )
    except Exception:
        await query.edit_message_text(
            detail_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

# =====================================================
# 💬 MESSAGE HANDLER  — search + AI
# =====================================================
# Per-user conversation history
chat_history: dict = {}

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = (update.message.text or "").strip()
    if not user_input or user_input.startswith("/"):
        return

    user_id = update.effective_user.id

    # ---- Channel Search ----
    search_results = [ch for ch in channels_cache if user_input.lower() in ch["name"].lower()]

    if search_results:
        await update.message.reply_chat_action(ChatAction.TYPING)

        if len(search_results) == 1:
            # Direct detail
            ch  = search_results[0]
            idx = channels_cache.index(ch)
            await send_channel_detail_msg(update, ch, idx)
        else:
            # List with pagination
            await send_channel_list(update.message, search_results, f"🔍 '{user_input}'",
                                    query_str=user_input)
    else:
        # ---- AI Response ----
        await update.message.reply_chat_action(ChatAction.TYPING)

        # Maintain per-user history
        history = chat_history.get(user_id, [])
        ai_reply = mi_ai_response(user_input, history)

        # Update history
        history.append({"role": "user",      "content": user_input})
        history.append({"role": "assistant", "content": ai_reply})
        chat_history[user_id] = history[-20:]  # Keep last 20 messages

        c = rand_color_batch(3)
        btns = [
            [
                InlineKeyboardButton(f"{c[0]} 📺 Channels",  callback_data="menu_search"),
                InlineKeyboardButton(f"{c[1]} 🆓 Free M3U",  callback_data="menu_m3u"),
            ],
            [
                InlineKeyboardButton(f"{c[2]} 🌐 Website",   url=WEBSITE_URL),
            ]
        ]

        await update.message.reply_text(
            f"🤖 *MI AI:*\n\n{ai_reply}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )

async def send_channel_detail_msg(update, ch, idx):
    name  = ch.get("name",  "Unknown")
    logo  = ch.get("logo",  "")
    group = ch.get("group", "General")
    url   = ch.get("url",   "")

    vlc_link = f"vlc://{url}"
    ns_link  = f"nsvideo://{url}"

    caption = (
        f"📺 *{name}*\n\n"
        f"🗂️ Category: `{group}`\n"
        f"✅ Stream Available\n\n"
        f"▶️ *Kisi bhi player mein chalayein:*"
    )

    c = rand_color_batch(5)
    btns = [
        [
            InlineKeyboardButton(f"{c[0]} ▶️ Direct Link", url=url),
            InlineKeyboardButton(f"{c[1]} 🎬 VLC",         url=vlc_link),
        ],
        [
            InlineKeyboardButton(f"{c[2]} 📺 NS Player",   url=ns_link),
            InlineKeyboardButton(f"{c[3]} 🌐 Website",     url=WEBSITE_URL),
        ],
        [InlineKeyboardButton(f"{c[4]} 🏠 Main Menu",      callback_data="menu_back")],
    ]
    kb = InlineKeyboardMarkup(btns)

    try:
        if logo and logo.startswith("http"):
            await update.message.reply_photo(photo=logo, caption=caption,
                                             reply_markup=kb, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(caption, reply_markup=kb, parse_mode="Markdown")

# =====================================================
# 🏠 GROUP / CHANNEL JOIN HANDLER
# =====================================================
async def greet_new_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jab bot kisi group ya channel mein add ho."""
    result = update.my_chat_member
    if result and result.new_chat_member.status in ("member", "administrator"):
        chat = update.effective_chat
        chat_name = chat.title or "Group"
        c = rand_color_batch(3)
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"✨ *Assalam-o-Alaikum {chat_name}!* ✨\n\n"
                    f"Main hoon *MI AI* 🤖 — MiTV Network ka IPTV + AI Assistant!\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📺 *{len(channels_cache):,}* Live Channels\n"
                    f"🔍 Channel search — bas naam likhein\n"
                    f"🤖 AI se baat — kuch bhi puchein\n"
                    f"🆓 Free M3U playlists\n"
                    f"📱 Player recommendations\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👇 *Start karen:*"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(f"{c[0]} 📺 Channel Search", callback_data="menu_search"),
                        InlineKeyboardButton(f"{c[1]} 🤖 AI Chat",        callback_data="menu_ai"),
                    ],
                    [
                        InlineKeyboardButton(f"{c[2]} 🌐 Website",        url=WEBSITE_URL),
                        InlineKeyboardButton("🏠 Main Menu",               callback_data="menu_back"),
                    ]
                ])
            )
        except Exception as e:
            print(f"Group greeting error: {e}")

# =====================================================
# ⌨️ COMMANDS
# =====================================================
async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 *Reloading channels...*", parse_mode="Markdown")
    load_m3u(force=True)
    await msg.edit_text(
        f"✅ *Done!* {len(channels_cache):,} channels loaded.",
        parse_mode="Markdown"
    )

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args).strip()
    if not q:
        await update.message.reply_text("🔍 Usage: `/search ARY News`", parse_mode="Markdown")
        return
    results = [ch for ch in channels_cache if q.lower() in ch["name"].lower()]
    if not results:
        await update.message.reply_text(f"😕 `{q}` — koi channel nahi mila.", parse_mode="Markdown")
        return
    await send_channel_list(update.message, results, f"🔍 '{q}'", query_str=q)

async def cmd_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = get_categories()
    lines = [f"• {c}: {n}" for c, n in list(cats.items())[:20]]
    await update.message.reply_text(
        "🗂️ *Top Categories:*\n\n" + "\n".join(lines),
        parse_mode="Markdown"
    )

async def cmd_m3u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    colors = rand_color_batch(len(FREE_M3U_LINKS))
    btns   = [[InlineKeyboardButton(f"{colors[i]} {m['name']}", url=m['url'])]
               for i, m in enumerate(FREE_M3U_LINKS)]
    await update.message.reply_text(
        "🆓 *Free M3U Links:*\n\n⚠️ Use karne ke liye pehle bot start karen!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(btns)
    )

async def cmd_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    colors = rand_color_batch(len(PLAYERS))
    btns   = [[InlineKeyboardButton(f"{colors[i]} {name}", url=url)]
               for i, (name, url) in enumerate(PLAYERS.items())]
    await update.message.reply_text(
        "📱 *IPTV Players — Recommended:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(btns)
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ *MI AI — Commands List*\n\n"
        "/start — Main menu kholein\n"
        "/search `<name>` — Channel search karein\n"
        "/categories — Sabhi categories dekhein\n"
        "/m3u — Free M3U playlist links\n"
        "/players — IPTV player apps\n"
        "/reload — Channels refresh karen\n"
        "/help — Yeh help message\n\n"
        "💬 *Ya seedha channel ka naam type karein!*\n\n"
        f"🌐 {WEBSITE_URL}",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args).strip()
    if not q:
        await update.message.reply_text(
            "🤖 *AI Chat*\n\nSawaal seedha type karein!\n"
            "Ya `/ai Aapka sawaal yahan`",
            parse_mode="Markdown"
        )
        return
    await update.message.reply_chat_action(ChatAction.TYPING)
    reply = mi_ai_response(q)
    await update.message.reply_text(f"🤖 *MI AI:*\n\n{reply}", parse_mode="Markdown")

# =====================================================
# ⚙️ SETUP BOT COMMANDS  (Telegram menu)
# =====================================================
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start",      "Main menu kholein"),
        BotCommand("search",     "Channel search"),
        BotCommand("categories", "All categories"),
        BotCommand("m3u",        "Free M3U links"),
        BotCommand("players",    "IPTV players"),
        BotCommand("reload",     "Channels reload"),
        BotCommand("ai",         "AI se poochein"),
        BotCommand("help",       "Help guide"),
    ])
    print("✅ Bot commands registered!")

# =====================================================
# 🚀 MAIN
# =====================================================
if __name__ == '__main__':
    print("🚀 Starting MI AI Bot — Pro Edition...")
    load_m3u()

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("reload",     cmd_reload))
    app.add_handler(CommandHandler("search",     cmd_search))
    app.add_handler(CommandHandler("categories", cmd_categories))
    app.add_handler(CommandHandler("m3u",        cmd_m3u))
    app.add_handler(CommandHandler("players",    cmd_players))
    app.add_handler(CommandHandler("help",       cmd_help))
    app.add_handler(CommandHandler("ai",         cmd_ai))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))

    # Group/Channel join
    app.add_handler(ChatMemberHandler(greet_new_group, ChatMemberHandler.MY_CHAT_MEMBER))

    print(f"✅ MI AI Pro is Online! Channels: {len(channels_cache):,}")
    app.run_polling(drop_pending_updates=True)
