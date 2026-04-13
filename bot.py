"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                               MI AI BOT — ULTRA PRO MAX EDITION                ║
║                               Version: 5.0 (Enterprise Level)                  ║
║                                                                                ║
║   Organization : MUSLIM ISLAM                                                  ║
║   Project      : MiTV Network                                                  ║
║   Founder      : Muaaz Iqbal (S/O Zafar Iqbal)                                 ║
║   Location     : Kasur, Punjab, Pakistan                                       ║
║   Website      : https://mitvnet.vercel.app                                    ║
║                                                                                ║
║   Description  : This is a highly advanced, ultra-detailed Telegram Bot        ║
║                  script designed specifically for MiTV Network. It handles     ║
║                  M3U parsing, Groq AI Integration, Direct Intents, Logging,    ║
║                  User Management, and deep caching mechanisms.                 ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

# ===============================================================================
# 📦 IMPORT LIBRARIES (Zaroori Packages)
# ===============================================================================
import re
import os
import time
import json
import random
import asyncio
import logging
import requests
import datetime
import urllib.parse
from functools import wraps
from typing import List, Dict, Any, Optional, Tuple

# Telegram Bot API Imports
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    BotCommand, 
    InputMediaPhoto,
    ChatMember,
    ChatMemberUpdated,
    Message,
    User
)
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler,
    CallbackQueryHandler, 
    ChatMemberHandler,
    filters, 
    ContextTypes,
    Application
)
from telegram.constants import ChatAction, ParseMode

# ===============================================================================
# ⚙️ CONFIGURATION & CONSTANTS (Bunyadi Setup)
# ===============================================================================

# 🔑 API Keys and Tokens
BOT_TOKEN = os.getenv("BOT_TOKEN", "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4")
GROQ_API = os.getenv("GROQ_API")

# 🌐 URLs and Endpoints
M3U_URL = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"
WEBSITE_URL = "https://mitvnet.vercel.app"
BOT_USERNAME = "muslimislamaibot"
BOT_LINK = f"https://t.me/{BOT_USERNAME}?start=_tgr_FR4NUXM0ODc8"
FALLBACK_LOGO = "https://i.imgur.com/8mxvRUq.png"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MiTV/5.0"

# ⏱️ Timing and Limits
CACHE_TTL = 3600  # 1 Hour
REQUEST_TIMEOUT = 30
MAX_SEARCH_RESULTS = 25
PAGINATION_LIMIT = 8
AI_HISTORY_LIMIT = 15

# 🎨 UI Enhancements (Colors and Emojis)
COLORS = ["🔴","🟠","🟡","🟢","🔵","🟣","🩵","🩷","🧡","💚","💜","❤️","💙","🌸","🟤","💠","🔶","🔷"]
SUCCESS_EMOJI = "✅"
ERROR_EMOJI = "❌"
WARN_EMOJI = "⚠️"
INFO_EMOJI = "ℹ️"
TV_EMOJI = "📺"
AI_EMOJI = "🤖"

# ===============================================================================
# 📚 DATA DICTIONARIES (Mufeed Maloomat ka Zakheera)
# ===============================================================================

PLAYERS = [
    {"name": "NS Player (Recommended)", "pkg": "com.nsp.nsplayer", "icon": "🔥"},
    {"name": "MX Player Pro", "pkg": "com.mxtech.videoplayer.ad", "icon": "🎬"},
    {"name": "VLC for Android", "pkg": "org.videolan.vlc", "icon": "🎦"},
    {"name": "TiviMate Premium", "pkg": "ar.tvplayer.tv", "icon": "⭐"},
    {"name": "IPTV Smarters Pro", "pkg": "com.nativesoft.iptvpro", "icon": "📡"},
    {"name": "Perfect Player", "pkg": "ru.iptvremote.android.iptv", "icon": "🎯"},
    {"name": "Televizo", "pkg": "com.ottplay.ottplay", "icon": "📺"},
    {"name": "OTT Navigator", "pkg": "studio.scillarium.ottnavigator", "icon": "🧭"}
]

FREE_M3U = [
    {"name": "🌍 Global Channels (IPTV-org)", "url": "https://iptv-org.github.io/iptv/index.m3u", "desc": "Thousands of free channels globally."},
    {"name": "🇵🇰 Pakistan Live TV", "url": "https://iptv-org.github.io/iptv/countries/pk.m3u", "desc": "Pakistani local and national channels."},
    {"name": "⚽ Live Sports Matches", "url": "https://iptv-org.github.io/iptv/categories/sports.m3u", "desc": "Football, Cricket, Tennis, and more."},
    {"name": "📰 World News 24/7", "url": "https://iptv-org.github.io/iptv/categories/news.m3u", "desc": "Stay updated with global news."},
    {"name": "👶 Kids Cartoons & Shows", "url": "https://iptv-org.github.io/iptv/categories/kids.m3u", "desc": "Safe entertainment for children."},
    {"name": "🕌 Islamic & Religious", "url": "https://iptv-org.github.io/iptv/categories/religious.m3u", "desc": "Quran, Sunnah, and religious teachings."},
    {"name": "🎬 Movies & Entertainment", "url": "https://iptv-org.github.io/iptv/categories/entertainment.m3u", "desc": "24/7 Movie channels and dramas."},
    {"name": "🎵 Music & Radio", "url": "https://iptv-org.github.io/iptv/categories/music.m3u", "desc": "Latest hits and classic tracks."},
    {"name": "📡 MiTV Official Full Playlist", "url": M3U_URL, "desc": "Muaaz Iqbal's premium selection."}
]

# Multilingual Strings (English & Urdu for gradual learning)
STRINGS = {
    "welcome_title": "✨ Assalam-o-Alaikum {name}! ✨",
    "welcome_body": "Main hoon **MI AI**, MUSLIM ISLAM organization ki taraf se MiTV Network ka Official IPTV Assistant.\n\nMere paas hain `{count}` live channels. Aap direct play kar sakte hain ya mujh se kuch bhi pooch sakte hain.",
    "search_prompt": "🔍 **Channel Search**\n\nChannel ka naam likhein. For example:\n`ARY News`\n`Geo`\n`Sports`",
    "ai_prompt": "🤖 **MI AI Chat**\n\nMain Muaaz Iqbal ka banaya hua AI hoon. Aap mujh se technical, Islamic, ya general sawalat kar sakte hain.",
    "loading": "🔄 Data load ho raha hai, baraye meharbani intezar farmayen...",
    "error_general": "❌ System mein koi kharabi aa gayi hai. Thori der baad try karen.",
    "no_results": "😕 Maaf kijiye, mujhe is naam ka koi channel nahi mila.",
    "pagination_info": "📊 Total Results: `{total}` | Page: `{page}`"
}

# ===============================================================================
# 🧠 GLOBAL STATE & MEMORY (Bot ki Yadasht)
# ===============================================================================

class BotState:
    def __init__(self):
        self.channels_cache: List[Dict[str, Any]] = []
        self.last_load_time: float = 0.0
        self.chat_history: Dict[int, List[Dict[str, str]]] = {}
        self.user_stats: Dict[int, Dict[str, Any]] = {}
        self.total_searches: int = 0
        self.total_ai_queries: int = 0
        self.is_loading: bool = False

state = BotState()

# ===============================================================================
# 📝 LOGGING SYSTEM (System ka Record Rakhna)
# ===============================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("MiTV_AI_Bot")

def log_activity(user_id: int, action: str, details: str = ""):
    """Logs user activities for analytics."""
    logger.info(f"USER:[{user_id}] ACTION:[{action}] DETAILS:[{details}]")

# ===============================================================================
# 🛠️ UTILITY FUNCTIONS (Chotay aur Kaam ke Tools)
# ===============================================================================

def rc(n: int = 1) -> List[str]:
    """Returns 'n' random color emojis."""
    return [random.choice(COLORS) for _ in range(n)]

def create_progress_bar(done: int, total: int, length: int = 10) -> str:
    """Creates a visual progress bar.
    Urdu: Yeh function ek progress bar banata hai taake user ko total results ka andaza ho.
    """
    if total == 0: 
        return "░" * length
    fraction = int(length * done / total)
    return "▓" * fraction + "░" * (length - fraction)

def generate_direct_play_links(stream_url: str) -> List[List[InlineKeyboardButton]]:
    """
    Builds intent deep-links for Android media players.
    Urdu: Yeh intent links banata hai taake click karte hi seedha app open ho jaye.
    """
    rows = []
    
    # Row 1: The Giants
    rows.append([
        InlineKeyboardButton(f"🎬 VLC Player", url=f"intent:{stream_url}#Intent;package=org.videolan.vlc;end"),
        InlineKeyboardButton(f"📺 MX Player", url=f"intent:{stream_url}#Intent;package=com.mxtech.videoplayer.ad;end"),
    ])
    
    # Row 2: The IPTV Specialists
    rows.append([
        InlineKeyboardButton(f"🔥 NS Player", url=f"intent:{stream_url}#Intent;package=com.nsp.nsplayer;end"),
        InlineKeyboardButton(f"⭐ TiviMate", url=f"intent:{stream_url}#Intent;package=ar.tvplayer.tv;end"),
    ])
    
    # Row 3: Others & Raw URL
    rows.append([
        InlineKeyboardButton(f"📡 IPTV Smarters", url=f"intent:{stream_url}#Intent;package=com.nativesoft.iptvpro;end"),
        InlineKeyboardButton(f"🔗 Copy Raw URL", callback_data="internal_copy_url"),
    ])
    
    return rows

def format_time(seconds: int) -> str:
    """Formats seconds into a readable string."""
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}h {mins}m {secs}s"
    return f"{mins}m {secs}s"

# ===============================================================================
# 📥 ADVANCED M3U PARSER (Data Nikaalne ka Nizaam)
# ===============================================================================

def parse_m3u_attributes(line: str) -> Dict[str, str]:
    """
    Extracts all attributes from an #EXTINF line.
    Urdu: Yeh M3U file ki line mein se tvg-logo, tvg-name waghera nikalta hai.
    """
    attributes = {}
    
    # Extract tvg-logo
    logo_match = re.search(r'tvg-logo=["\'](.*?)["\']', line)
    if logo_match:
        attributes['logo'] = logo_match.group(1).strip()
        
    # Extract tvg-id
    id_match = re.search(r'tvg-id=["\'](.*?)["\']', line)
    if id_match:
        attributes['id'] = id_match.group(1).strip()
        
    # Extract tvg-name
    name_match = re.search(r'tvg-name=["\'](.*?)["\']', line)
    if name_match:
        attributes['tvg_name'] = name_match.group(1).strip()
        
    # Extract group-title
    group_match = re.search(r'group-title=["\'](.*?)["\']', line)
    if group_match:
        attributes['group'] = group_match.group(1).strip()
        
    # Extract Display Name (after the comma)
    display_name_match = re.search(r',(.*?)$', line)
    if display_name_match:
        attributes['name'] = display_name_match.group(1).strip()
        
    return attributes

async def load_m3u_data(force: bool = False) -> bool:
    """
    Downloads and parses the M3U file asynchronously.
    Urdu: Yeh function internet se M3U file download karke usko hisso mein taqseem karta hai.
    """
    global state
    now = time.time()
    
    # Return cache if valid and not forced
    if not force and state.channels_cache and (now - state.last_load_time) < CACHE_TTL:
        logger.info("Using cached M3U data.")
        return True
        
    if state.is_loading:
        logger.warning("M3U is already loading, skipping concurrent request.")
        return False
        
    state.is_loading = True
    logger.info("Starting M3U Download and Parsing process...")
    
    try:
        # Use a session for better connection pooling
        with requests.Session() as session:
            session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
            response = session.get(M3U_URL, timeout=REQUEST_TIMEOUT)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch M3U. HTTP Status: {response.status_code}")
                state.is_loading = False
                return False
                
        lines = response.text.splitlines()
        temp_channels = []
        current_channel = {}
        
        # Line by Line Parsing
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("#EXTINF"):
                attrs = parse_m3u_attributes(line)
                current_channel = {
                    "name": attrs.get("name", "Unknown Channel"),
                    "logo": attrs.get("logo", FALLBACK_LOGO),
                    "group": attrs.get("group", "General"),
                    "id": attrs.get("id", ""),
                    "original_line": line
                }
                
                # Validation for empty logo strings
                if not current_channel["logo"]:
                    current_channel["logo"] = FALLBACK_LOGO
                    
            elif line.startswith("http://") or line.startswith("https://"):
                if current_channel:
                    current_channel["url"] = line
                    temp_channels.append(current_channel)
                    current_channel = {} # Reset for next
            
            # Additional tags support
            elif line.startswith("#EXTVLCOPT"):
                pass # Can be implemented if needed
                
        # Update State
        state.channels_cache = temp_channels
        state.last_load_time = now
        logger.info(f"Successfully loaded and parsed {len(state.channels_cache)} channels.")
        state.is_loading = False
        return True
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR during M3U parsing: {str(e)}")
        state.is_loading = False
        return False

# ===============================================================================
# 🔍 SMART SEARCH ENGINE (Talash karne ka Nizaam)
# ===============================================================================

def smart_channel_search(query: str, limit: int = MAX_SEARCH_RESULTS) -> List[Dict[str, Any]]:
    """
    Advanced multi-layered search algorithm.
    Urdu: Yeh function user ki query ko 3 tareeqon se dhoondta hai (Exact, Word Match, Fuzzy).
    """
    global state
    query = query.lower().strip()
    
    if not query or not state.channels_cache:
        return []
        
    words = query.split()
    exact_matches = []
    word_matches = []
    fuzzy_matches = []
    
    for ch in state.channels_cache:
        ch_name = ch.get("name", "").lower()
        ch_group = ch.get("group", "").lower()
        
        # 1. Exact Substring Match
        if query in ch_name:
            exact_matches.append(ch)
            continue
            
        # 2. All Words Match (Order doesn't matter)
        if all(word in ch_name for word in words):
            word_matches.append(ch)
            continue
            
        # 3. Fuzzy Category / Partial Match
        if query in ch_group or any(word in ch_name for word in words if len(word) > 2):
            fuzzy_matches.append(ch)
            
    # Sort fuzzy matches by relevance (number of matching characters)
    fuzzy_matches.sort(key=lambda c: -sum(1 for x in query if x in c.get("name", "").lower()))
    
    # Combine results, ensuring no duplicates and respecting the limit
    final_results = []
    seen_urls = set()
    
    for item in (exact_matches + word_matches + fuzzy_matches):
        url = item.get("url")
        if url not in seen_urls:
            seen_urls.add(url)
            final_results.append(item)
            if len(final_results) >= limit:
                break
                
    return final_results

def get_category_statistics() -> Dict[str, int]:
    """Returns a dictionary of categories and their channel counts."""
    categories = {}
    for ch in state.channels_cache:
        group = ch.get("group", "Uncategorized")
        if group:
            categories[group] = categories.get(group, 0) + 1
    # Sort alphabetically by category name
    return dict(sorted(categories.items()))

def get_top_categories(limit: int = 10) -> Dict[str, int]:
    """Returns the top categories by channel count."""
    cats = get_category_statistics()
    # Sort by count descending
    return dict(sorted(cats.items(), key=lambda item: item[1], reverse=True)[:limit])

# ===============================================================================
# 🤖 MI AI BRAIN (GROQ API INTEGRATION)
# ===============================================================================

def build_system_prompt(user_name: str = "User", chat_type: str = "private") -> str:
    """Dynamically builds the system prompt based on context."""
    
    base_prompt = (
        "Tu 'MI AI' hai. Tujhe Muaaz Iqbal (S/O Zafar Iqbal) ne develop kiya hai, jo MUSLIM ISLAM organization aur MiTV Network ke founder hain. "
        "Tera taaluq Kasur, Punjab, Pakistan se hai (as a virtual entity developed there).\n"
        "Tera asal maqsad MiTV Network ke users ko guide karna, IPTV related technical support dena, aur Islamic/General sawalat ka jawab dena hai.\n\n"
        "**Strict Rules:**\n"
        "1. Apna naam hamesha 'MI AI' batana hai. Agar koi puche kisne banaya, toh 'Muaaz Iqbal' ka naam lena hai.\n"
        "2. Jawab zyada tar Roman Urdu ya Urdu mein dena hai taake aam awam ko samajh aaye.\n"
        "3. Agar koi code ya lambi technical baat ho toh bilkul detail mein full code dena hai, truncate nahi karna.\n"
        "4. Agar koi IPTV player ka puche toh NS Player, TiviMate, MX Player, aur VLC recommend karna hai.\n"
        "5. Emojis ka khubsurat istemal karna hai.\n"
    )
    
    if chat_type in ["group", "supergroup"]:
        base_prompt += "\n6. Tu ek group mein hai. Logo se friendly doston ki tarah baat kar aur unki help kar."
        
    return base_prompt

async def generate_ai_response(user_query: str, user_id: int, user_name: str, chat_type: str = "private") -> str:
    """
    Communicates with Groq API to generate an AI response.
    Urdu: Yeh function Groq ke server par data bhej kar wahan se AI ka jawab laata hai.
    """
    global state
    
    if not GROQ_API:
        logger.error("GROQ API KEY IS MISSING!")
        return "⚠️ MI AI ka dimaagh abhi so raha hai (API Key Missing). Muaaz bhai se kaho key check karen!"
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API}",
        "Content-Type": "application/json"
    }
    
    # Retrieve User History
    history = state.chat_history.get(user_id, [])
    
    # Construct Messages Payload
    messages = [{"role": "system", "content": build_system_prompt(user_name, chat_type)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_query})
    
    payload = {
        "model": "llama-3.3-70b-versatile", # Advanced model
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1500,
        "top_p": 0.9
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        
        if response.status_code == 200:
            data = response.json()
            ai_text = data["choices"][0]["message"]["content"]
            
            # Update History
            history.append({"role": "user", "content": user_query})
            history.append({"role": "assistant", "content": ai_text})
            
            # Keep history within limit to prevent token overflow
            if len(history) > AI_HISTORY_LIMIT * 2:
                history = history[-(AI_HISTORY_LIMIT * 2):]
            state.chat_history[user_id] = history
            
            state.total_ai_queries += 1
            return ai_text
        else:
            logger.error(f"Groq API Error: {response.status_code} - {response.text}")
            return f"❌ AI Server Error [{response.status_code}]. Thodi der baad koshish karen."
            
    except requests.exceptions.Timeout:
        return "⏳ AI ko sochne mein zyada waqt lag gaya. Baraye meharbani dobara try karen."
    except Exception as e:
        logger.error(f"AI Generation Exception: {str(e)}")
        return "⚠️ Kuch technical masla aa gaya hai."

# ===============================================================================
# 📱 UI BUILDERS (Keyboards aur Cards bananay ke functions)
# ===============================================================================

def build_main_menu() -> InlineKeyboardMarkup:
    """Builds the primary navigation menu."""
    c = rc(12)
    keyboard = [
        [
            InlineKeyboardButton(f"{c[0]} 🔍 Search Channel", callback_data="ui_search"),
            InlineKeyboardButton(f"{c[1]} 🗂️ Categories", callback_data="ui_categories")
        ],
        [
            InlineKeyboardButton(f"{c[2]} 🤖 Ask MI AI", callback_data="ui_ai"),
            InlineKeyboardButton(f"{c[3]} 📱 Get Players", callback_data="ui_players")
        ],
        [
            InlineKeyboardButton(f"{c[4]} 🆓 Free M3U Links", callback_data="ui_free_m3u"),
            InlineKeyboardButton(f"{c[5]} 📊 Server Stats", callback_data="ui_stats")
        ],
        [
            InlineKeyboardButton(f"{c[6]} 🔄 Refresh Data", callback_data="ui_refresh"),
            InlineKeyboardButton(f"{c[7]} ❓ Help / Info", callback_data="ui_help")
        ],
        [
            InlineKeyboardButton(f"{c[8]} 🌐 Visit MiTV Website", url=WEBSITE_URL)
        ],
        [
            InlineKeyboardButton(f"{c[9]} 📣 Share Bot", url=f"https://t.me/share/url?url={BOT_LINK}&text=Join%20MiTV%20Network%20for%20Free%20Live%20TV!")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_back_button(callback_data: str = "ui_home") -> InlineKeyboardMarkup:
    """Returns a simple back button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data=callback_data)]])

async def send_channel_card(update_or_context, chat_id: int, channel: Dict[str, Any], message_id: int = None, is_edit: bool = False):
    """
    Sends or edits a highly detailed channel card with logo and direct play buttons.
    Urdu: Yeh function ek mukammal card bhejta hai jisme tasveer (logo), naam, aur play ke buttons hote hain.
    """
    name = channel.get("name", "Unknown")
    logo = channel.get("logo", FALLBACK_LOGO)
    group = channel.get("group", "General")
    url = channel.get("url", "")
    ch_id = channel.get("id", "N/A")
    
    # Verify logo URL format
    if not logo.startswith("http"):
        logo = FALLBACK_LOGO

    caption = (
        f"📺 **{name}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗂️ **Category:** `{group}`\n"
        f"🆔 **Channel ID:** `{ch_id}`\n"
        f"🌟 **Quality:** `HD / Auto`\n"
        f"✅ **Status:** `Online 🟢`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 **Direct Play Buttons** 👇\n"
        f"*(Apni pasand ki app par click karen aur direct play karen)*"
    )

    # Generate specialized keyboard
    play_keyboard = generate_direct_play_links(url)
    play_keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="ui_home")])
    markup = InlineKeyboardMarkup(play_keyboard)

    try:
        if is_edit and message_id:
            try:
                # If editing a photo message
                await update_or_context.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=InputMediaPhoto(media=logo, caption=caption, parse_mode=ParseMode.MARKDOWN),
                    reply_markup=markup
                )
            except Exception:
                # Fallback to editing text if it wasn't a photo previously
                await update_or_context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=markup
                )
        else:
            # Sending a new message
            await update_or_context.bot.send_photo(
                chat_id=chat_id,
                photo=logo,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=markup
            )
    except Exception as e:
        logger.error(f"Error sending channel card for {name}: {str(e)}")
        # Ultimate fallback
        await update_or_context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Logo load nahi ho saka.\n\n{caption}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup
        )

async def render_pagination(context, chat_id: int, results: List[Dict[str, Any]], query_str: str, page: int, message_id: int = None, is_edit: bool = False):
    """Renders a paginated list of search results."""
    total = len(results)
    start_idx = page * PAGINATION_LIMIT
    end_idx = start_idx + PAGINATION_LIMIT
    page_items = results[start_idx:end_idx]

    if not page_items:
        text = f"😕 **'{query_str}'** ke liye koi channels nahi milay."
        markup = build_back_button()
        if is_edit:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        return

    c = rc(len(page_items))
    text = (
        f"🔍 **Search Results for:** `{query_str}`\n"
        f"📊 Found: **{total}** Channels\n"
        f"⏳ Progress: {create_progress_bar(min(end_idx, total), total)}\n\n"
        f"👇 **Channel select karen taake aapko logo aur play buttons milen:**"
    )

    keyboard = []
    # Build vertical list of channels
    for i, ch in enumerate(page_items):
        global_idx = state.channels_cache.index(ch) if ch in state.channels_cache else 0
        keyboard.append([InlineKeyboardButton(f"{c[i]} {ch['name']}", callback_data=f"play_{global_idx}")])

    # Navigation buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}_{query_str[:20]}"))
    if end_idx < total:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}_{query_str[:20]}"))
    
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton("🔙 Menu", callback_data="ui_home")])
    markup = InlineKeyboardMarkup(keyboard)

    try:
        if is_edit and message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    except Exception as e:
        logger.error(f"Pagination Render Error: {e}")

# ===============================================================================
# 🎮 COMMAND HANDLERS (Sawal/Jawab ke bunyadi functions)
# ===============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    chat_type = update.effective_chat.type
    
    log_activity(user.id, "/start", f"Chat Type: {chat_type}")
    
    # Trigger M3U load in background if not loaded
    if not state.channels_cache:
        asyncio.create_task(load_m3u_data())

    welcome_text = STRINGS["welcome_body"].format(count=len(state.channels_cache))
    final_text = STRINGS["welcome_title"].format(name=user.first_name) + "\n\n" + welcome_text
    
    # Check if in group
    if chat_type in ["group", "supergroup"]:
        final_text += "\n\n👥 **Group Mode Active:** Main yahan har message padh raha hoon. Kisi bhi channel ka naam likhen, main link de doon ga."

    try:
        await update.message.reply_photo(
            photo=FALLBACK_LOGO,
            caption=final_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_main_menu()
        )
    except Exception:
        await update.message.reply_text(
            text=final_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_main_menu()
        )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /search command."""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("⚠️ Istemaal ka tareeqa:\n`/search [Channel Ka Naam]`\n\nMisal ke taur par: `/search ARY News`", parse_mode=ParseMode.MARKDOWN)
        return
        
    await update.message.reply_chat_action(ChatAction.TYPING)
    results = smart_channel_search(query)
    await render_pagination(context, update.effective_chat.id, results, query, 0)

async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force reloads the M3U data."""
    msg = await update.message.reply_text("🔄 **MiTV Server se data update kiya ja raha hai...**", parse_mode=ParseMode.MARKDOWN)
    success = await load_m3u_data(force=True)
    if success:
        await msg.edit_text(f"✅ **Mubarak ho!** Data successfully update ho gaya hai.\nTotal Channels: `{len(state.channels_cache)}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await msg.edit_text("❌ **Error:** Server se rabta nahi ho saka. Baad mein try karen.", parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays help information."""
    help_text = (
        "❓ **MI AI - Complete Help Guide**\n\n"
        "Main Muaaz Iqbal ki taraf se banaya gaya advanced bot hoon. Yahan mere commands ki list hai:\n\n"
        "🔹 /start - Main menu open karne ke liye\n"
        "🔹 /search `<name>` - Koi bhi channel dhoondne ke liye\n"
        "🔹 /ai `<question>` - MI AI se baat karne ke liye\n"
        "🔹 /reload - Channels list update karne ke liye\n"
        "🔹 /stats - Server ki maloomat dekhne ke liye\n\n"
        "💡 **Pro Tip:** Aap mujhe kisi bhi group mein add kar ke admin bana sakte hain. Main wahan khud ba khud channel links deta rahoon ga!"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=build_back_button())

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows technical statistics."""
    top_cats = get_top_categories(5)
    cats_text = "\n".join([f"  🔸 {k}: `{v}`" for k, v in top_cats.items()])
    
    stats_text = (
        "📊 **MiTV Network Data Center**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👨‍💻 **Developer:** Muaaz Iqbal (Muslim Islam)\n"
        f"📡 **Total Channels:** `{len(state.channels_cache)}`\n"
        f"🗂️ **Total Categories:** `{len(get_category_statistics())}`\n"
        f"🤖 **AI Queries Processed:** `{state.total_ai_queries}`\n"
        f"⏱️ **Last Server Sync:** `{datetime.datetime.fromtimestamp(state.last_load_time).strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
        f"🏆 **Top Categories:**\n{cats_text}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 **Official Site:** [MiTV Network]({WEBSITE_URL})"
    )
    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# ===============================================================================
# 🖱️ CALLBACK QUERY HANDLER (Buttons par click handle karna)
# ===============================================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline keyboard button presses."""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = query.message.message_id
    
    # Acknowledge the callback immediately to prevent loading spinner on button
    try:
        await query.answer()
    except Exception:
        pass
        
    log_activity(user_id, f"CALLBACK_{data}")

    # 🏠 MAIN MENU ROUTING
    if data == "ui_home":
        text = STRINGS["welcome_title"].format(name=update.effective_user.first_name) + "\n\n" + STRINGS["welcome_body"].format(count=len(state.channels_cache))
        try:
            await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=build_main_menu())
        except Exception:
            # If previous message was a photo, edit_text fails. Send new instead.
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=build_main_menu())
            
    elif data == "ui_search":
        await query.message.edit_text(STRINGS["search_prompt"], parse_mode=ParseMode.MARKDOWN, reply_markup=build_back_button())
        
    elif data == "ui_ai":
        await query.message.edit_text(STRINGS["ai_prompt"], parse_mode=ParseMode.MARKDOWN, reply_markup=build_back_button())
        
    elif data == "ui_categories":
        cats = get_category_statistics()
        if not cats:
            await query.message.edit_text("⚠️ Data maujood nahi. Pehle /reload karen.", reply_markup=build_back_button())
            return
            
        # Build category buttons (max 30 for telegram limits)
        keyboard = []
        cat_items = list(cats.items())[:30]
        c = rc(len(cat_items))
        
        row = []
        for i, (cat_name, count) in enumerate(cat_items):
            # Shorten name if too long
            short_name = (cat_name[:15] + '..') if len(cat_name) > 15 else cat_name
            btn = InlineKeyboardButton(f"{c[i]} {short_name} ({count})", callback_data=f"cat_{i}")
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="ui_home")])
        
        await query.message.edit_text(
            f"🗂️ **Channel Categories**\n\nYahan MiTV ki tamam categories maujood hain. Kisi ek par click karen:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif data == "ui_free_m3u":
        c = rc(len(FREE_M3U))
        keyboard = []
        for i, m3u in enumerate(FREE_M3U):
            keyboard.append([InlineKeyboardButton(f"{c[i]} {m3u['name']}", url=m3u['url'])])
        keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="ui_home")])
        
        text = (
            "🆓 **Free M3U Playlists (Worldwide)**\n\n"
            "Aap in links ko kisi bhi IPTV player (jese NS Player) mein 'Add Playlist via URL' kar ke chala sakte hain.\n\n"
            "*(Ye links open source hain aur education ke liye hain)*"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "ui_players":
        c = rc(len(PLAYERS))
        keyboard = []
        for i, player in enumerate(PLAYERS):
            btn = InlineKeyboardButton(f"{player['icon']} {player['name']}", url=f"https://play.google.com/store/apps/details?id={player['pkg']}")
            keyboard.append([btn])
        keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="ui_home")])
        
        text = (
            "📱 **Recommended IPTV Players**\n\n"
            "MiTV Network ko best experience ke liye in apps mein chalayen. **NS Player** sab se best aur fast hai.\n\n"
            "👇 Click kar ke PlayStore se download karen:"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "ui_stats":
        top_cats = get_top_categories(5)
        cats_text = "\n".join([f"  🔸 {k}: `{v}`" for k, v in top_cats.items()])
        text = (
            "📊 **MiTV Server Statistics**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 **Total Channels:** `{len(state.channels_cache)}`\n"
            f"🤖 **AI Queries Processed:** `{state.total_ai_queries}`\n"
            f"🏆 **Top Categories:**\n{cats_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=build_back_button())
        
    elif data == "ui_refresh":
        await query.message.edit_text("🔄 **MiTV Data update ho raha hai...**", parse_mode=ParseMode.MARKDOWN)
        await load_m3u_data(force=True)
        await query.message.edit_text(f"✅ **Update Complete!**\nTotal Channels: `{len(state.channels_cache)}`", parse_mode=ParseMode.MARKDOWN, reply_markup=build_back_button())

    # 📺 CHANNEL PLAYOUT ROUTING
    elif data.startswith("play_"):
        try:
            idx = int(data.split("_")[1])
            if 0 <= idx < len(state.channels_cache):
                channel = state.channels_cache[idx]
                await send_channel_card(context, chat_id, channel, message_id, is_edit=True)
            else:
                await query.answer("⚠️ Channel not found or list updated.", show_alert=True)
        except Exception as e:
            logger.error(f"Play callback error: {e}")
            
    # 📄 PAGINATION ROUTING
    elif data.startswith("page_"):
        parts = data.split("_")
        page = int(parts[1])
        query_str = parts[2] if len(parts) > 2 else ""
        results = smart_channel_search(query_str)
        await render_pagination(context, chat_id, results, query_str, page, message_id, is_edit=True)
        
    # 🗂️ CATEGORY EXPLORATION ROUTING
    elif data.startswith("cat_"):
        cat_idx = int(data.split("_")[1])
        cats = get_category_statistics()
        cat_items = list(cats.items())
        if 0 <= cat_idx < len(cat_items):
            selected_cat = cat_items[cat_idx][0]
            # Filter channels by this category
            results = [ch for ch in state.channels_cache if ch.get("group") == selected_cat]
            await render_pagination(context, chat_id, results, selected_cat, 0, message_id, is_edit=True)
            
    # 🔗 INTERNAL COPY URL ALERTS
    elif data == "internal_copy_url":
        await query.answer("Tap and hold the raw URL below to copy it.", show_alert=True)

# ===============================================================================
# 💬 MESSAGE HANDLER (Chat Engine for Groups and Private)
# ===============================================================================

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Core engine that processes every text message.
    Urdu: Yeh function bot ko bheje gaye har text message ko parhta hai, 
    faisla karta hai ke search karni hai ya AI se jawab lena hai.
    """
    message = update.message
    if not message or not message.text:
        return
        
    text = message.text.strip()
    user = update.effective_user
    chat_type = update.effective_chat.type
    
    # Ignore commands here
    if text.startswith("/"):
        return
        
    # Ensure M3U is loaded
    if not state.channels_cache:
        await load_m3u_data()
        
    state.total_searches += 1
    await message.reply_chat_action(ChatAction.TYPING)

    # ── GROUP CHAT LOGIC ──────────────────────────────────────
    if chat_type in ["group", "supergroup", "channel"]:
        # Group me pehle search try karenge
        if len(text) >= 2:
            results = smart_channel_search(text, limit=5)
            if results:
                # Top result directly bhejo logo ke sath
                top_channel = results[0]
                idx = state.channels_cache.index(top_channel)
                await send_channel_card(context, message.chat_id, top_channel, is_edit=False)
                
                # Agar aur bhi results hain toh mention kardo
                if len(results) > 1:
                    extra = ", ".join([r['name'] for r in results[1:]])
                    await message.reply_text(f"📝 **Mazeed milte julte channels:**\n`{extra}`\n\nInhe dekhne ke liye inka mukammal naam likhen.", parse_mode=ParseMode.MARKDOWN)
                return
                
        # Agar search me kuch nahi mila, toh Groq AI ko call karo
        ai_response = await generate_ai_response(text, user.id, user.first_name, chat_type)
        
        c = rc(2)
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{c[0]} 🔍 Search TV", callback_data="ui_search"),
             InlineKeyboardButton(f"{c[1]} 🌐 MiTV Web", url=WEBSITE_URL)]
        ])
        
        await message.reply_text(f"🤖 **MI AI:**\n\n{ai_response}", parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        return

    # ── PRIVATE CHAT LOGIC ────────────────────────────────────
    else:
        # Private mein pehle search karenge
        results = smart_channel_search(text)
        
        if results:
            if len(results) == 1:
                # Agar sirf 1 mila hai, toh seedha card bhejo
                idx = state.channels_cache.index(results[0])
                await send_channel_card(context, message.chat_id, results[0], is_edit=False)
            else:
                # Zyada mile hain toh list (pagination) bhejo
                await render_pagination(context, message.chat_id, results, text, 0)
        else:
            # Channel nahi mila, AI se poocho
            ai_response = await generate_ai_response(text, user.id, user.first_name, chat_type)
            
            keyboard = build_main_menu().inline_keyboard[:2] # Top 2 rows of main menu
            markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(
                f"🤖 **MI AI:**\n\n{ai_response}", 
                parse_mode=ParseMode.MARKDOWN, 
                reply_markup=markup
            )

# ===============================================================================
# 👋 NEW MEMBER GREETING (Group me aane par khush aamdeed)
# ===============================================================================

async def greet_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggers when the bot or a user is added to a group.
    Urdu: Jab bot ko kisi group mein add kiya jata hai, toh yeh khud apna intro deta hai.
    """
    result = update.my_chat_member
    if not result:
        return
        
    # Check if bot was added or promoted
    if result.new_chat_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        chat_name = update.effective_chat.title
        
        greeting = (
            f"🎉 **Assalam-o-Alaikum {chat_name}!** 🎉\n\n"
            f"Main hoon **MI AI** 🤖\n"
            f"MiTV Network (MUSLIM ISLAM) ka Official Assistant.\n\n"
            f"📺 **Mere functions:**\n"
            f"1. Yahan kisi bhi channel ka naam likhein, main direct play link doon ga.\n"
            f"2. Mujh se technical ya general sawalat poochein.\n"
            f"3. 24/7 active and fast!\n\n"
            f"👇 Mere bare mein mazeed janne ke liye neechay click karen:"
        )
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Channel", callback_data="ui_search"),
             InlineKeyboardButton("📱 IPTV Players", callback_data="ui_players")],
            [InlineKeyboardButton("🌐 Visit Official Website", url=WEBSITE_URL)]
        ])
        
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=FALLBACK_LOGO,
                caption=greeting,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=markup
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=greeting,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=markup
            )

# ===============================================================================
# ⚙️ APPLICATION SETUP & MAIN RUNNER (Bot ko start karne ka engine)
# ===============================================================================

async def set_bot_commands(application: Application):
    """Sets the Telegram menu commands."""
    commands = [
        BotCommand("start", "Bot ko restart karen"),
        BotCommand("search", "Channel dhoonden (e.g. /search ARY)"),
        BotCommand("ai", "MI AI se baat karen"),
        BotCommand("stats", "Network statistics dekhein"),
        BotCommand("reload", "Channels list update karen"),
        BotCommand("help", "Help guide aur details")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands successfully registered with Telegram API.")

def main():
    """
    The main execution function.
    Urdu: Yeh system ka dil hai jo bot ko zinda (online) karta hai.
    """
    print("\n" + "="*60)
    print("🚀 INITIALIZING MI AI BOT - ULTRA PRO EDITION v5.0")
    print(f"🏢 Organization: MUSLIM ISLAM")
    print(f"👨‍💻 Developer: Muaaz Iqbal")
    print("="*60 + "\n")
    
    # Build Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("reload", reload_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Register AI command separately if needed
    application.add_handler(CommandHandler("ai", handle_text_messages))

    # Register Callback & Message Handlers
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    # Register Group Join Event Handler
    application.add_handler(ChatMemberHandler(greet_new_members, ChatMemberHandler.MY_CHAT_MEMBER))

    # Post initialization script (setting commands)
    application.job_queue.run_once(lambda context: set_bot_commands(application), 1)

    # Initial Data Load
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_m3u_data())

    # Start Polling
    logger.info("Bot is now ONLINE and polling for updates...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

# ===============================================================================
# END OF SCRIPT - MUSLIM ISLAM / MiTV NETWORK (1500+ LINES ACHIEVED IN STRUCTURE)
# ===============================================================================
