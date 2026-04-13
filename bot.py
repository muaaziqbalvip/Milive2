"""
╔══════════════════════════════════════════════════════════╗
║          MI AI BOT — ULTRA PRO EDITION v3.0              ║
║      MiTV Network  |  Developer: Muaaz Iqbal             ║
║      mitvnet.vercel.app  |  @muslimislamaibot             ║
╚══════════════════════════════════════════════════════════╝
Features:
  Channel logo shown with every result (from M3U tvg-logo)
  Direct play buttons: VLC / MX Player / NS Player / TiviMate / Smarters
  Full channel detail with stream URL copy
  Smart fuzzy AI search system
  AI auto-replies to EVERY group/channel message
  Auto greeting when added to group/channel (no admin needed)
  Free M3U links (require bot start first)
  Random color buttons on every response
  Pagination for large results
  Per-user AI conversation history (context-aware)
"""

import re, os, time, random, requests, urllib.parse
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler,
    filters, ContextTypes
)
from telegram.constants import ChatAction

# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════
TOKEN        = os.getenv("BOT_TOKEN", "8328897413:AAEw05JlW3hLGaROkX_njjEqTFaQQMA_yO4")
M3U_URL      = "https://mitv-tan.vercel.app/api/m3u?user=MITV-94120"
GROQ_API     = os.getenv("GROQ_API")
WEBSITE_URL  = "https://mitvnet.vercel.app"
BOT_USERNAME = "muslimislamaibot"
BOT_LINK     = f"https://t.me/{BOT_USERNAME}?start=_tgr_FR4NUXM0ODc8"
CACHE_TTL    = 3600
FALLBACK_LOGO = "https://i.imgur.com/8mxvRUq.png"

COLORS = ["🔴","🟠","🟡","🟢","🔵","🟣","🩵","🩷","🧡","💚","💜","❤️","💙","🌸","🟤"]

PLAYERS = [
    {"name": "NS Player",      "pkg": "com.nsp.nsplayer"},
    {"name": "MX Player",      "pkg": "com.mxtech.videoplayer.ad"},
    {"name": "VLC",            "pkg": "org.videolan.vlc"},
    {"name": "TiviMate",       "pkg": "ar.tvplayer.tv"},
    {"name": "IPTV Smarters",  "pkg": "com.nativesoft.iptvpro"},
    {"name": "Perfect Player", "pkg": "ru.iptvremote.android.iptv"},
]

FREE_M3U = [
    {"name": "🌍 Global (IPTV-org)",  "url": "https://iptv-org.github.io/iptv/index.m3u"},
    {"name": "🇵🇰 Pakistan",          "url": "https://iptv-org.github.io/iptv/countries/pk.m3u"},
    {"name": "⚽ Sports",             "url": "https://iptv-org.github.io/iptv/categories/sports.m3u"},
    {"name": "📰 News",               "url": "https://iptv-org.github.io/iptv/categories/news.m3u"},
    {"name": "👶 Kids",               "url": "https://iptv-org.github.io/iptv/categories/kids.m3u"},
    {"name": "🕌 Islamic/Religious",  "url": "https://iptv-org.github.io/iptv/categories/religious.m3u"},
    {"name": "🎬 Entertainment",      "url": "https://iptv-org.github.io/iptv/categories/entertainment.m3u"},
    {"name": "📡 MiTV Full Playlist", "url": M3U_URL},
]

# ══════════════════════════════════════════════
# GLOBAL STATE
# ══════════════════════════════════════════════
channels_cache: list  = []
last_load_time: float = 0
chat_history:   dict  = {}   # user_id -> list of {role, content}

# ══════════════════════════════════════════════
# UTILS
# ══════════════════════════════════════════════
def rc(n=1):
    return [random.choice(COLORS) for _ in range(n)]

def bar(done, total, length=8):
    if total == 0: return "░" * length
    f = int(length * done / total)
    return "▓" * f + "░" * (length - f)

def play_buttons(stream_url: str) -> list:
    """
    Build player rows using Android intent deep-links.
    User taps -> app opens and plays directly.
    """
    rows = []
    rows.append([
        InlineKeyboardButton("🎬 VLC",       url=f"intent:{stream_url}#Intent;package=org.videolan.vlc;end"),
        InlineKeyboardButton("📺 MX Player", url=f"intent:{stream_url}#Intent;package=com.mxtech.videoplayer.ad;end"),
    ])
    rows.append([
        InlineKeyboardButton("🔥 NS Player", url=f"intent:{stream_url}#Intent;package=com.nsp.nsplayer;end"),
        InlineKeyboardButton("⭐ TiviMate",  url=f"intent:{stream_url}#Intent;package=ar.tvplayer.tv;end"),
    ])
    rows.append([
        InlineKeyboardButton("📡 Smarters",  url=f"intent:{stream_url}#Intent;package=com.nativesoft.iptvpro;end"),
        InlineKeyboardButton("🔗 Direct URL",url=stream_url),
    ])
    return rows

# ══════════════════════════════════════════════
# M3U PARSER
# ══════════════════════════════════════════════
def load_m3u(force=False):
    global channels_cache, last_load_time
    now = time.time()
    if not force and channels_cache and (now - last_load_time) < CACHE_TTL:
        return
    print("🔄 Loading M3U...")
    try:
        r = requests.get(M3U_URL, timeout=30)
        if r.status_code != 200:
            print(f"❌ HTTP {r.status_code}")
            return
        lines = r.text.splitlines()
        temp, item = [], {}
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                nm  = re.search(r',(.+)',              line)
                lg  = re.search(r'tvg-logo="(.+?)"',   line)
                gr  = re.search(r'group-title="(.+?)"', line)
                tid = re.search(r'tvg-id="(.+?)"',      line)
                item = {
                    "name":  nm.group(1).strip() if nm else "Unknown",
                    "logo":  lg.group(1)          if lg else FALLBACK_LOGO,
                    "group": gr.group(1)          if gr else "General",
                    "id":    tid.group(1)         if tid else "",
                }
            elif line.startswith("http") and item:
                item["url"] = line
                temp.append(item)
                item = {}
        channels_cache = temp
        last_load_time = now
        print(f"✅ {len(channels_cache)} channels loaded!")
    except Exception as e:
        print(f"❌ M3U error: {e}")

def smart_search(q: str, limit=20) -> list:
    q     = q.lower().strip()
    words = q.split()
    if not q or not channels_cache:
        return []
    exact, wmatch, fuzzy = [], [], []
    for ch in channels_cache:
        n = ch["name"].lower()
        if q in n:
            exact.append(ch)
        elif all(w in n for w in words):
            wmatch.append(ch)
        elif any(w in n for w in words if len(w) > 1):
            fuzzy.append(ch)
    fuzzy.sort(key=lambda c: -sum(1 for x in q if x in c["name"].lower()))
    return (exact + wmatch + fuzzy)[:limit]

def get_cats() -> dict:
    cats = {}
    for ch in channels_cache:
        g = ch.get("group","General")
        cats[g] = cats.get(g, 0) + 1
    return dict(sorted(cats.items(), key=lambda x: -x[1]))

# ══════════════════════════════════════════════
# MI AI (GROQ)
# ══════════════════════════════════════════════
SYS = (
    "Tu MI AI hai — Muaaz Iqbal ka banaya hua smart AI assistant.\n"
    "Tu MiTV Network (mitvnet.vercel.app) ka official assistant hai.\n\n"
    "Teri khasiyatein:\n"
    "- IPTV channels dhundhna aur detail dena\n"
    "- NS Player, MX Player, VLC, TiviMate, IPTV Smarters setup\n"
    "- M3U playlist troubleshooting\n"
    "- Islamic channels aur content recommend karna\n"
    "- General knowledge aur friendly baatein\n"
    "- Group discussions mein naturally participate karna\n\n"
    "Rules:\n"
    "- Roman Urdu mein jawab do (jab tak user English mein na likhe)\n"
    "- Apna naam MI AI hai — ChatGPT ya koi aur mat kaho\n"
    "- Short, clear, helpful jawab do\n"
    "- Emojis naturally use karo\n"
    "- Channel search ke liye: naam type karne ki guide karo\n"
    "- Group mein natural member ki tarah baat karo\n"
)

def mi_ai(text: str, history: list = None, ctx: str = "") -> str:
    if not GROQ_API:
        return f"⚠️ MI AI offline hai. Visit: {WEBSITE_URL}"
    sys = SYS + (f"\nContext: {ctx}" if ctx else "")
    msgs = [{"role": "system", "content": sys}]
    if history:
        msgs.extend(history[-12:])
    msgs.append({"role": "user", "content": text})
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": msgs,
                  "temperature": 0.7, "max_tokens": 600},
            timeout=20
        )
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"😕 Thoda issue aa gaya. Dobara try karen!"

# ══════════════════════════════════════════════
# CHANNEL CARD SENDER (logo + full detail + players)
# ══════════════════════════════════════════════
async def send_card(target, ch: dict, idx: int, edit=False):
    name  = ch.get("name",  "Unknown")
    logo  = ch.get("logo",  FALLBACK_LOGO) or FALLBACK_LOGO
    group = ch.get("group", "General")
    url   = ch.get("url",   "")

    cap = (
        f"📺 *{name}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗂️  Category : `{group}`\n"
        f"✅  Status    : Live Stream\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"▶️ *Player button dabayein — stream turant chalega!*"
    )

    rows = play_buttons(url)
    c    = rc(3)
    rows.append([
        InlineKeyboardButton(f"{c[0]} 📋 URL Copy",   callback_data=f"url_{idx}"),
        InlineKeyboardButton(f"{c[1]} 🌐 MiTV Site",  url=WEBSITE_URL),
    ])
    rows.append([InlineKeyboardButton(f"{c[2]} 🏠 Main Menu", callback_data="menu_back")])
    kb = InlineKeyboardMarkup(rows)

    if edit:
        try:
            await target.edit_message_media(
                media=InputMediaPhoto(media=logo, caption=cap, parse_mode="Markdown"),
                reply_markup=kb
            )
            return
        except Exception:
            pass
        try:
            await target.edit_message_text(cap, parse_mode="Markdown", reply_markup=kb)
            return
        except Exception:
            pass
    else:
        try:
            await target.reply_photo(photo=logo, caption=cap,
                                     parse_mode="Markdown", reply_markup=kb)
            return
        except Exception:
            pass
        try:
            await target.reply_text(cap, parse_mode="Markdown", reply_markup=kb)
        except Exception as e:
            print(f"Card error: {e}")

async def send_list(target, results: list, title: str,
                    page=0, qstr="", back="menu_back", edit=False):
    PER   = 8
    total = len(results)
    s, e  = page * PER, page * PER + PER
    page_r = results[s:e]

    if not page_r:
        txt = f"😕 *{title}*\n\nKoi channel nahi mila."
        kb  = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=back)]])
        if edit:
            await target.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb)
        else:
            await target.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    c   = rc(len(page_r))
    txt = (
        f"🔍 *{title}*\n"
        f"📊 Mila: *{total}*  {bar(min(e,total), total)}  {min(e,total)}/{total}\n\n"
        f"👇 *Channel chunein — Logo + Detail milegi:*"
    )

    btns = []
    for i, ch in enumerate(page_r):
        gi = s + i
        btns.append([InlineKeyboardButton(f"{c[i]} 📺 {ch['name']}", callback_data=f"chd_{gi}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"chp_{page-1}_{qstr[:28]}"))
    if e < total:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"chp_{page+1}_{qstr[:28]}"))
    if nav:
        btns.append(nav)
    btns.append([InlineKeyboardButton("🔙 Back", callback_data=back)])
    kb = InlineKeyboardMarkup(btns)

    if edit:
        await target.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb)
    else:
        await target.reply_text(txt, parse_mode="Markdown", reply_markup=kb)

# ══════════════════════════════════════════════
# MAIN MENU
# ══════════════════════════════════════════════
def main_kb():
    c = rc(10)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{c[0]} 🔍 Channel Search", callback_data="menu_search"),
            InlineKeyboardButton(f"{c[1]} 🗂️ Categories",     callback_data="menu_cats"),
        ],
        [
            InlineKeyboardButton(f"{c[2]} 🆓 Free M3U",       callback_data="menu_m3u"),
            InlineKeyboardButton(f"{c[3]} 📱 Players",        callback_data="menu_players"),
        ],
        [
            InlineKeyboardButton(f"{c[4]} 🤖 AI Chat",        callback_data="menu_ai"),
            InlineKeyboardButton(f"{c[5]} 📊 Stats",          callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton(f"{c[6]} 🌐 Website",        url=WEBSITE_URL),
            InlineKeyboardButton(f"{c[7]} 📲 Share Bot",      url=f"https://t.me/share/url?url={BOT_LINK}"),
        ],
        [
            InlineKeyboardButton(f"{c[8]} 🔄 Reload",         callback_data="menu_reload"),
            InlineKeyboardButton(f"{c[9]} ❓ Help",           callback_data="menu_help"),
        ],
    ])

# ══════════════════════════════════════════════
# START
# ══════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_m3u()
    fname = (update.effective_user.first_name or "Dost")
    await update.message.reply_text(
        f"✨ *Assalam-o-Alaikum {fname}!* ✨\n\n"
        f"🤖 Main hoon *MI AI*\n"
        f"MiTV Network ka Official IPTV + AI Assistant!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 *{len(channels_cache):,}* Live Channels (logos ke saath)\n"
        f"▶️ Direct play — VLC, MX, NS, TiviMate\n"
        f"🤖 AI — kuch bhi puchein\n"
        f"🆓 Free M3U playlists\n"
        f"💬 Group mein bhi kaam karta hai\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 *Menu se option chunen:*",
        parse_mode="Markdown",
        reply_markup=main_kb(),
        disable_web_page_preview=True
    )

# ══════════════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════════════
async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()

    # Channel detail
    if data.startswith("chd_"):
        idx = int(data[4:])
        if 0 <= idx < len(channels_cache):
            await send_card(q, channels_cache[idx], idx, edit=True)
        return

    # Channel pagination
    if data.startswith("chp_"):
        parts = data.split("_", 2)
        page  = int(parts[1])
        qstr  = parts[2] if len(parts) > 2 else ""
        res   = smart_search(qstr) if qstr else channels_cache[:80]
        await send_list(q, res, f"🔍 '{qstr}'", page=page, qstr=qstr, edit=True)
        return

    # Show stream URL in alert
    if data.startswith("url_"):
        idx = int(data[4:])
        if 0 <= idx < len(channels_cache):
            url = channels_cache[idx].get("url", "")
            await q.answer(url[:200], show_alert=True)
        return

    # Category channels
    if data.startswith("catc_"):
        cat = data[5:]
        res = [ch for ch in channels_cache if ch.get("group","").startswith(cat)]
        await send_list(q, res, f"📂 {cat}", back="menu_cats", edit=True)
        return

    # Menu items
    if data == "menu_search":
        await q.edit_message_text(
            "🔍 *Smart Channel Search*\n\n"
            "Channel ka naam type karein!\n\n"
            "💡 *Examples:*\n"
            "`ARY News` · `Geo TV` · `Star Plus`\n"
            "`PTV Sports` · `Discovery` · `CNN`\n"
            "`Islam` · `Quran` · `Cartoon`\n\n"
            "🤖 _Thoda galat likho tab bhi match milega!_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]])
        )
        return

    if data == "menu_cats":
        cats = get_cats()
        if not cats:
            await q.edit_message_text("⚠️ /reload try karen.")
            return
        c    = rc(min(len(cats), 24))
        btns = [InlineKeyboardButton(f"{c[i]} {cat} ({cnt})", callback_data=f"catc_{cat[:28]}")
                for i, (cat, cnt) in enumerate(list(cats.items())[:24])]
        kb   = [btns[i:i+2] for i in range(0, len(btns), 2)]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
        await q.edit_message_text(
            f"🗂️ *Channel Categories*\n\n"
            f"Total: *{len(channels_cache):,}* channels · *{len(cats)}* categories\n\n"
            f"Category chunein:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if data == "menu_m3u":
        c    = rc(len(FREE_M3U))
        btns = [[InlineKeyboardButton(f"{c[i]} {m['name']}", url=m['url'])]
                 for i, m in enumerate(FREE_M3U)]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
        await q.edit_message_text(
            "🆓 *Free M3U Playlist Links*\n\n"
            "⚠️ *Zaruri:* Pehle bot start karen:\n"
            f"👉 [Bot Start Link]({BOT_LINK})\n\n"
            "Phir kisi bhi IPTV player mein paste karen!\n"
            "📱 NS Player / TiviMate best hain.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns),
            disable_web_page_preview=True
        )
        return

    if data == "menu_players":
        c    = rc(len(PLAYERS))
        btns = [[InlineKeyboardButton(f"{c[i]} {p['name']}",
                 url=f"https://play.google.com/store/apps/details?id={p['pkg']}")]
                 for i, p in enumerate(PLAYERS)]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
        await q.edit_message_text(
            "📱 *IPTV Players — Recommended*\n\n"
            "🏆 *Best IPTV:*\n"
            "  • NS Player — Sabse smooth for IPTV\n"
            "  • TiviMate — EPG + Professional UI\n\n"
            "🎬 *Best Video:*\n"
            "  • MX Player — Most popular\n"
            "  • VLC — Open source, har format\n\n"
            "📡 *IPTV Smarters Pro — All-in-one*\n\n"
            "Install karen, M3U link paste karen — enjoy!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return

    if data == "menu_ai":
        await q.edit_message_text(
            "🤖 *MI AI — Smart Chat Mode*\n\n"
            "Main in topics mein help kar sakta hoon:\n\n"
            "📺 IPTV channels dhundhna\n"
            "📱 Player setup (NS, MX, VLC, TiviMate)\n"
            "🔗 M3U playlist issues\n"
            "🕌 Islamic channels aur content\n"
            "💬 General knowledge\n"
            "🛠️ Technical IPTV problems\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 *Seedha apna sawaal type karein!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]])
        )
        return

    if data == "menu_stats":
        cats = get_cats()
        top5 = list(cats.items())[:5]
        t5   = "\n".join([f"  {i+1}. {c}: *{n}*" for i,(c,n) in enumerate(top5)])
        await q.edit_message_text(
            f"📊 *MiTV Network — Stats*\n\n"
            f"🌐 {WEBSITE_URL}\n"
            f"👨‍💻 Developer: Muaaz Iqbal\n"
            f"🤖 Bot: @{BOT_USERNAME}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📺 Total Channels: *{len(channels_cache):,}*\n"
            f"🗂️ Categories: *{len(cats)}*\n"
            f"⏰ {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
            f"🏆 *Top 5 Categories:*\n{t5}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Website", url=WEBSITE_URL)],
                [InlineKeyboardButton("🔙 Back",    callback_data="menu_back")]
            ])
        )
        return

    if data == "menu_reload":
        await q.edit_message_text("🔄 *Reload ho raha hai...*", parse_mode="Markdown")
        load_m3u(force=True)
        await q.edit_message_text(
            f"✅ *Done!*\n📺 *{len(channels_cache):,}* channels loaded\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="menu_back")]])
        )
        return

    if data == "menu_help":
        await q.edit_message_text(
            "❓ *Help Guide — MI AI Bot*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔍 *Channel Search:*\n"
            "  Naam type karen: `ARY`, `Geo`, `Discovery`\n\n"
            "▶️ *Channel Chalana:*\n"
            "  Channel → Player button dabayein\n"
            "  App khulti hai, stream shuru!\n\n"
            "🆓 *Free M3U:*\n"
            "  Bot start karen pehle\n\n"
            "🤖 *AI Chat:*\n"
            "  Koi bhi sawaal Roman Urdu mein\n\n"
            "👥 *Group mein:*\n"
            "  Kuch bhi likhen — AI jawab dega!\n"
            "  Channel naam likhein — results aayenge\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📞 Support: {WEBSITE_URL}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Website", url=WEBSITE_URL)],
                [InlineKeyboardButton("🔙 Back",    callback_data="menu_back")]
            ])
        )
        return

    if data == "menu_back":
        load_m3u()
        user  = update.effective_user
        fname = (user.first_name or "Dost") if user else "Dost"
        await q.edit_message_text(
            f"✨ *Assalam-o-Alaikum {fname}!* ✨\n\n"
            f"🤖 *MI AI* — MiTV Network IPTV Assistant\n\n"
            f"📺 *{len(channels_cache):,}* Channels\n"
            f"🌐 {WEBSITE_URL}\n\n"
            f"👇 *Menu se option chunen:*",
            parse_mode="Markdown",
            reply_markup=main_kb(),
            disable_web_page_preview=True
        )
        return

# ══════════════════════════════════════════════
# MESSAGE HANDLER — private + group auto AI
# ══════════════════════════════════════════════
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    if not msg or not msg.text:
        return
    text   = msg.text.strip()
    uid    = update.effective_user.id
    chat_t = update.effective_chat.type

    if text.startswith("/"):
        return

    load_m3u()

    # ── GROUP / SUPERGROUP / CHANNEL ─────────────────
    if chat_t in ("group", "supergroup", "channel"):
        await msg.reply_chat_action(ChatAction.TYPING)

        results = smart_search(text, limit=8) if len(text) >= 2 else []

        if results:
            # Send top channel card (with logo)
            ch  = results[0]
            idx = channels_cache.index(ch)
            await send_card(msg, ch, idx)

            # If multiple results, show buttons for others
            if len(results) > 1:
                c    = rc(min(len(results)-1, 5))
                more = []
                for i, r in enumerate(results[1:5]):
                    ri = channels_cache.index(r)
                    more.append([InlineKeyboardButton(f"{c[i]} {r['name']}", callback_data=f"chd_{ri}")])
                more.append([InlineKeyboardButton("🌐 MiTV", url=WEBSITE_URL)])

                # Short AI note about channel
                ai_note = mi_ai(
                    f"'{ch['name']}' channel ke baare mein 1-2 lines mein batao.",
                    chat_history.get(uid)
                )
                await msg.reply_text(
                    f"🤖 *MI AI:* {ai_note}\n\n"
                    f"📺 *{len(results)} channels mile — baqi:*",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(more)
                )
        else:
            # Pure AI conversation
            hist  = chat_history.get(uid, [])
            reply = mi_ai(text, hist)
            hist.append({"role": "user",      "content": text})
            hist.append({"role": "assistant", "content": reply})
            chat_history[uid] = hist[-14:]

            c = rc(2)
            await msg.reply_text(
                f"🤖 *MI AI:*\n\n{reply}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"{c[0]} 📺 Channels", callback_data="menu_search"),
                    InlineKeyboardButton(f"{c[1]} 🌐 MiTV",     url=WEBSITE_URL),
                ]])
            )
        return

    # ── PRIVATE CHAT ─────────────────────────────────
    await msg.reply_chat_action(ChatAction.TYPING)
    results = smart_search(text, limit=20)

    if results:
        if len(results) == 1:
            await send_card(msg, results[0], channels_cache.index(results[0]))
        else:
            await send_list(msg, results, f"🔍 '{text}'", qstr=text)
    else:
        hist  = chat_history.get(uid, [])
        reply = mi_ai(text, hist)
        hist.append({"role": "user",      "content": text})
        hist.append({"role": "assistant", "content": reply})
        chat_history[uid] = hist[-14:]

        c = rc(4)
        await msg.reply_text(
            f"🤖 *MI AI:*\n\n{reply}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"{c[0]} 📺 Channels",  callback_data="menu_search"),
                    InlineKeyboardButton(f"{c[1]} 🆓 M3U",       callback_data="menu_m3u"),
                ],
                [
                    InlineKeyboardButton(f"{c[2]} 📱 Players",   callback_data="menu_players"),
                    InlineKeyboardButton(f"{c[3]} 🌐 Website",   url=WEBSITE_URL),
                ],
            ])
        )

# ══════════════════════════════════════════════
# GROUP / CHANNEL JOIN — auto greeting
# ══════════════════════════════════════════════
async def on_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result:
        return
    if result.new_chat_member.status not in ("member", "administrator"):
        return

    chat      = update.effective_chat
    chat_name = chat.title or "Group"
    load_m3u()
    c = rc(4)

    txt = (
        f"🎉 *Assalam-o-Alaikum {chat_name}!* 🎉\n\n"
        f"Main hoon *MI AI* 🤖\n"
        f"MiTV Network ka Official IPTV + AI Assistant!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 *{len(channels_cache):,}* Live Channels (logos ke saath)\n"
        f"▶️ Direct play: VLC · MX · NS · TiviMate\n"
        f"🤖 AI — kuch bhi puchein\n"
        f"🔍 Smart channel search\n"
        f"🆓 Free M3U playlists\n"
        f"💬 Group mein har sawaal ka jawab\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌐 {WEBSITE_URL}\n\n"
        f"👇 *Ab start karen:*"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{c[0]} 🔍 Channel Search", callback_data="menu_search"),
            InlineKeyboardButton(f"{c[1]} 🆓 Free M3U",       callback_data="menu_m3u"),
        ],
        [
            InlineKeyboardButton(f"{c[2]} 📱 Players",        callback_data="menu_players"),
            InlineKeyboardButton(f"{c[3]} 🤖 AI Chat",        callback_data="menu_ai"),
        ],
        [
            InlineKeyboardButton("🌐 MiTV Website",            url=WEBSITE_URL),
            InlineKeyboardButton("🏠 Full Menu",               callback_data="menu_back"),
        ],
    ])
    try:
        await context.bot.send_photo(
            chat_id=chat.id, photo=FALLBACK_LOGO,
            caption=txt, parse_mode="Markdown", reply_markup=kb
        )
    except Exception:
        try:
            await context.bot.send_message(
                chat_id=chat.id, text=txt,
                parse_mode="Markdown", reply_markup=kb,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Join greeting error: {e}")

# ══════════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════════
async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await update.message.reply_text("🔄 Reloading...")
    load_m3u(force=True)
    await m.edit_text(f"✅ *{len(channels_cache):,} channels loaded!*", parse_mode="Markdown")

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args).strip()
    if not q:
        await update.message.reply_text("Usage: `/search ARY News`", parse_mode="Markdown"); return
    res = smart_search(q)
    if not res:
        await update.message.reply_text(f"😕 `{q}` — nahi mila.", parse_mode="Markdown"); return
    if len(res) == 1:
        await send_card(update.message, res[0], channels_cache.index(res[0]))
    else:
        await send_list(update.message, res, f"🔍 '{q}'", qstr=q)

async def cmd_cats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats  = get_cats()
    lines = [f"{i+1}. {c} — *{n}*" for i,(c,n) in enumerate(list(cats.items())[:20])]
    await update.message.reply_text("🗂️ *Top Categories:*\n\n" + "\n".join(lines), parse_mode="Markdown")

async def cmd_m3u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c    = rc(len(FREE_M3U))
    btns = [[InlineKeyboardButton(f"{c[i]} {m['name']}", url=m['url'])] for i,m in enumerate(FREE_M3U)]
    await update.message.reply_text(
        "🆓 *Free M3U Links*\n\n⚠️ Pehle bot start karen!",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns)
    )

async def cmd_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c    = rc(len(PLAYERS))
    btns = [[InlineKeyboardButton(f"{c[i]} {p['name']}",
             url=f"https://play.google.com/store/apps/details?id={p['pkg']}")]
             for i,p in enumerate(PLAYERS)]
    await update.message.reply_text("📱 *Recommended IPTV Players:*",
                                     parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args).strip()
    if not q:
        await update.message.reply_text("Usage: `/ai Aapka sawaal`", parse_mode="Markdown"); return
    await update.message.reply_chat_action(ChatAction.TYPING)
    reply = mi_ai(q, chat_history.get(update.effective_user.id))
    await update.message.reply_text(f"🤖 *MI AI:*\n\n{reply}", parse_mode="Markdown")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ *MI AI Bot — Commands*\n\n"
        "/start — Main menu\n"
        "/search `naam` — Channel search\n"
        "/categories — Sabhi categories\n"
        "/m3u — Free M3U links\n"
        "/players — IPTV player apps\n"
        "/ai `sawaal` — AI se poochein\n"
        "/reload — Channels refresh\n"
        "/help — Yeh help\n\n"
        "💬 *Seedha naam type karen — AI ya channel milega!*\n"
        "👥 *Group mein add karen — bina admin ke bhi kaam karta hai!*\n\n"
        f"🌐 {WEBSITE_URL}",
        parse_mode="Markdown", disable_web_page_preview=True
    )

# ══════════════════════════════════════════════
# POST INIT
# ══════════════════════════════════════════════
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start",      "Main menu kholein"),
        BotCommand("search",     "Channel search karen"),
        BotCommand("categories", "Sabhi categories"),
        BotCommand("m3u",        "Free M3U links"),
        BotCommand("players",    "IPTV player apps"),
        BotCommand("ai",         "AI se poochein"),
        BotCommand("reload",     "Channels reload"),
        BotCommand("help",       "Help guide"),
    ])
    print("✅ Commands menu set!")

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
if __name__ == "__main__":
    print("╔═══════════════════════════════════╗")
    print("║   MI AI BOT — ULTRA PRO v3.0      ║")
    print("║   MiTV Network | Muaaz Iqbal       ║")
    print("╚═══════════════════════════════════╝")

    load_m3u()

    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("reload",     cmd_reload))
    app.add_handler(CommandHandler("search",     cmd_search))
    app.add_handler(CommandHandler("categories", cmd_cats))
    app.add_handler(CommandHandler("m3u",        cmd_m3u))
    app.add_handler(CommandHandler("players",    cmd_players))
    app.add_handler(CommandHandler("ai",         cmd_ai))
    app.add_handler(CommandHandler("help",       cmd_help))

    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(ChatMemberHandler(on_join, ChatMemberHandler.MY_CHAT_MEMBER))

    print(f"✅ Online! {len(channels_cache):,} channels ready.")
    app.run_polling(drop_pending_updates=True)
