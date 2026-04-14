import os
import re
import json
import random
import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from fuzzywuzzy import process, fuzz
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
GROQ_API = os.getenv("GROQ_API")
AI_MODEL = "llama-3.3-70b-versatile"
STATS_FILE = "bot_stats.json"
HALF_HOUR = 1800  # 30 minutes in seconds

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
        self.active_groups = set()       # Groups + Channels registered
        self.chat_history = {}           # AI context per user
        self.user_registry = {}          # {user_id: {name, username, join_time, msg_count, last_seen}}
        self.group_registry = {}         # {chat_id: {title, type, join_time, msg_count}}
        self.total_searches = 0
        self.total_ai_chats = 0
        self.total_gift_sent = 0
        self.bot_start_time = datetime.now()

    def register_user(self, user):
        uid = user.id
        if uid not in self.user_registry:
            self.user_registry[uid] = {
                "name": user.full_name,
                "username": user.username or "N/A",
                "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "msg_count": 0,
                "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "searches": 0,
                "ai_chats": 0
            }
        else:
            self.user_registry[uid]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.user_registry[uid]["msg_count"] += 1
            self.user_registry[uid]["name"] = user.full_name

    def register_group(self, chat):
        cid = chat.id
        if cid not in self.group_registry:
            self.group_registry[cid] = {
                "title": chat.title or "Unknown",
                "type": chat.type,
                "joined": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "msg_count": 0
            }
        else:
            self.group_registry[cid]["msg_count"] += 1
            self.group_registry[cid]["title"] = chat.title or "Unknown"

bot_db = BotMemory()

# ==========================================
# 🎭 3. BEAUTIFUL GIF DATABASE (Premium)
# ==========================================
GIF_LIBRARY = {
    "greeting": [
        "https://media.giphy.com/media/ASd0Ukj0y3qMM/giphy.gif",
        "https://media.giphy.com/media/l0MYEqEzwMWFCg8rm/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcHhwcmRsM2ZxZTB0ZG9nZWI5Yng1bm9ndmFmeTVkbmw5dTV5bzZlcyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3oKIPnAiaMCws8nOsE/giphy.gif",
    ],
    "searching": [
        "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif",
        "https://media.giphy.com/media/26n6WywFabVnj2WzK/giphy.gif",
    ],
    "happy": [
        "https://media.giphy.com/media/chzz1FQgqhytWRWbp3/giphy.gif",
        "https://media.giphy.com/media/ZZkCo8zKWtt2ZgozfX/giphy.gif",
        "https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif",
    ],
    "gift": [
        "https://media.giphy.com/media/l3q2zbskZp2j8wniE/giphy.gif",
        "https://media.giphy.com/media/Wj7lNjMNDxSmc/giphy.gif",
        "https://media.giphy.com/media/ely3apij36BJhoZ234/giphy.gif",
    ],
    "tv": [
        "https://media.giphy.com/media/KzJ1vMKBgBqNwjpHr9/giphy.gif",
        "https://media.giphy.com/media/3ohs4rkYvzISB83cqY/giphy.gif",
    ],
    "confused": [
        "https://media.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif",
        "https://media.giphy.com/media/ISOckXUybVfQ4/giphy.gif",
    ],
    "fire": [
        "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
        "https://media.giphy.com/media/26BRv0ThflsHCqDrG/giphy.gif",
    ]
}

def get_gif(category):
    return random.choice(GIF_LIBRARY.get(category, GIF_LIBRARY["happy"]))

# ==========================================
# 🌐 4. ASYNC M3U LOADER (Fast & Reliable)
# ==========================================
async def fetch_m3u_async():
    logger.info("🔄 Fetching M3U from server...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(M3U_URL, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"❌ M3U Fetch Failed: {response.status}")
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

                        raw_logo = logo_match.group(1).strip() if logo_match else ""
                        # ✅ FIX: TVG logo properly validate karo
                        if raw_logo and raw_logo.startswith("http"):
                            final_logo = raw_logo
                        else:
                            final_logo = "https://via.placeholder.com/300x200/1a1a2e/ffffff?text=MiTV"

                        current_item = {
                            "name": name_match.group(1).strip() if name_match else "Unknown Channel",
                            "logo": final_logo,
                            "group": group_match.group(1).strip() if group_match else "General"
                        }
                    elif line.startswith("http"):
                        current_item["url"] = line
                        temp_list.append(current_item)
                        temp_names.append(current_item["name"])
                        current_item = {}

                bot_db.channels_cache = temp_list
                bot_db.channel_names = temp_names
                logger.info(f"✅ {len(bot_db.channels_cache)} channels loaded!")
    except Exception as e:
        logger.error(f"❌ M3U Loader Exception: {e}")

# ==========================================
# 🤖 5. GROQ AI ENGINE (Context Memory)
# ==========================================
async def get_ai_response(user_id, user_name, user_text):
    if not GROQ_API:
        return "⚠️ Bhai GROQ_API environment variable set nahi hai! Bot owner ko bolo."

    if user_id not in bot_db.chat_history:
        bot_db.chat_history[user_id] = deque(maxlen=8)

    bot_db.chat_history[user_id].append({"role": "user", "content": user_text})

    total_channels = len(bot_db.channels_cache)
    groups_count = len(bot_db.group_registry)

    system_prompt = (
        f"Tu MI AI hai — MiTV Network ka official smart assistant. "
        f"Tujhe Muaaz Iqbal ne banaya hai. Tera user {user_name} hai. "
        f"Tere paas abhi {total_channels} IPTV channels hain aur tu {groups_count} groups/channels mein active hai. "
        "Tu Roman Urdu/Hindi mein baat karta hai, bahut friendly aur zinda-dil hai. "
        "Emojis aur humor ka bharpoor istemal kar. Tech sawalon ka bhi tez jawab de. "
        "Agar koi channel maange to seedha bol ke /search ya channel ka naam likho. "
        "Hamesha confident, helpful aur energetic reh! 🚀"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(list(bot_db.chat_history[user_id]))

    headers = {"Authorization": f"Bearer {GROQ_API}", "Content-Type": "application/json"}
    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0.75,
        "max_tokens": 1024
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ai_reply = data["choices"][0]["message"]["content"]
                    bot_db.chat_history[user_id].append({"role": "assistant", "content": ai_reply})
                    bot_db.total_ai_chats += 1
                    return ai_reply
                else:
                    return "Yaar mera AI server nahi maan raha abhi 🤕 Thodi der baad try kar!"
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "Network jam gaya lagta hai 😅 Dobara message bhej!"

# ==========================================
# 🔍 6. SMART FUZZY CHANNEL SEARCH
# ==========================================
def find_channel_smartly(user_text):
    if not bot_db.channel_names:
        return None, None

    words = [w for w in user_text.split() if len(w) > 2]
    best_matches = []

    for word in words:
        matches = process.extract(word, bot_db.channel_names, limit=3, scorer=fuzz.token_set_ratio)
        for match in matches:
            if match[1] > 80:
                best_matches.append(match[0])

    if not best_matches:
        full_match = process.extractOne(user_text, bot_db.channel_names, scorer=fuzz.partial_ratio)
        if full_match and full_match[1] > 85:
            best_matches.append(full_match[0])

    if best_matches:
        results = [ch for ch in bot_db.channels_cache if ch['name'] in best_matches]
        unique_results = list({v['name']: v for v in results}.values())
        return True, unique_results

    return False, []

# ==========================================
# 📊 7. STATS HTML GENERATOR
# ==========================================
def generate_stats_html():
    uptime_delta = datetime.now() - bot_db.bot_start_time
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m"

    users_rows = ""
    for uid, data in sorted(bot_db.user_registry.items(), key=lambda x: x[1]['msg_count'], reverse=True):
        users_rows += f"""
        <tr>
            <td>{data['name']}</td>
            <td>@{data['username']}</td>
            <td><span class="badge">{data['msg_count']}</span></td>
            <td>{data.get('searches', 0)}</td>
            <td>{data.get('ai_chats', 0)}</td>
            <td>{data['first_seen']}</td>
            <td>{data['last_seen']}</td>
        </tr>"""

    groups_rows = ""
    for cid, data in sorted(bot_db.group_registry.items(), key=lambda x: x[1]['msg_count'], reverse=True):
        groups_rows += f"""
        <tr>
            <td>{data['title']}</td>
            <td><span class="type-badge type-{data['type']}">{data['type']}</span></td>
            <td>{data['msg_count']}</td>
            <td>{data['joined']}</td>
        </tr>"""

    # Top 10 channels by group
    group_counts = {}
    for ch in bot_db.channels_cache:
        g = ch.get('group', 'General')
        group_counts[g] = group_counts.get(g, 0) + 1
    top_groups = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    cat_rows = "".join(f"<tr><td>{g}</td><td>{c}</td></tr>" for g, c in top_groups)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MI AI Bot - Live Dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600;700&display=swap');

  :root {{
    --primary: #00d4ff;
    --secondary: #ff6b35;
    --accent: #7c3aed;
    --bg: #0a0a1a;
    --card: #111128;
    --card2: #161630;
    --text: #e2e8f0;
    --muted: #64748b;
    --success: #22c55e;
    --warning: #f59e0b;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Rajdhani', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }}

  /* Animated background */
  body::before {{
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: 
      radial-gradient(ellipse at 20% 20%, rgba(0,212,255,0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 80%, rgba(124,58,237,0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 60% 20%, rgba(255,107,53,0.05) 0%, transparent 40%);
    pointer-events: none;
    z-index: 0;
  }}

  .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; position: relative; z-index: 1; }}

  /* Header */
  .header {{
    text-align: center;
    padding: 40px 20px;
    margin-bottom: 40px;
    position: relative;
  }}
  .header::after {{
    content: '';
    position: absolute;
    bottom: 0; left: 20%; right: 20%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--primary), var(--accent), transparent);
  }}
  .logo {{
    font-family: 'Orbitron', monospace;
    font-size: clamp(28px, 5vw, 52px);
    font-weight: 900;
    background: linear-gradient(135deg, var(--primary), var(--accent), var(--secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 3px;
    animation: glow 2s ease-in-out infinite alternate;
  }}
  @keyframes glow {{
    from {{ filter: drop-shadow(0 0 10px rgba(0,212,255,0.3)); }}
    to {{ filter: drop-shadow(0 0 20px rgba(124,58,237,0.5)); }}
  }}
  .subtitle {{
    color: var(--muted);
    font-size: 16px;
    margin-top: 8px;
    letter-spacing: 2px;
    text-transform: uppercase;
  }}
  .live-badge {{
    display: inline-block;
    background: rgba(34,197,94,0.15);
    border: 1px solid var(--success);
    color: var(--success);
    padding: 4px 16px;
    border-radius: 20px;
    font-size: 13px;
    margin-top: 12px;
    letter-spacing: 2px;
  }}
  .live-badge::before {{
    content: '● ';
    animation: blink 1s infinite;
  }}
  @keyframes blink {{ 0%,100% {{opacity:1}} 50% {{opacity:0}} }}

  /* Stats Cards */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 40px;
  }}
  .stat-card {{
    background: var(--card);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.06);
    position: relative;
    overflow: hidden;
    transition: transform 0.3s, box-shadow 0.3s;
  }}
  .stat-card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 8px 32px rgba(0,212,255,0.15);
  }}
  .stat-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--gradient);
  }}
  .stat-card.blue {{ --gradient: linear-gradient(90deg, var(--primary), #0099cc); }}
  .stat-card.purple {{ --gradient: linear-gradient(90deg, var(--accent), #9f1fcc); }}
  .stat-card.orange {{ --gradient: linear-gradient(90deg, var(--secondary), #cc3300); }}
  .stat-card.green {{ --gradient: linear-gradient(90deg, var(--success), #15803d); }}
  .stat-card.yellow {{ --gradient: linear-gradient(90deg, var(--warning), #b45309); }}
  .stat-card.teal {{ --gradient: linear-gradient(90deg, #2dd4bf, #0891b2); }}

  .stat-icon {{ font-size: 36px; margin-bottom: 8px; }}
  .stat-value {{
    font-family: 'Orbitron', monospace;
    font-size: 32px;
    font-weight: 700;
    color: var(--primary);
  }}
  .stat-label {{
    font-size: 13px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
  }}

  /* Section Titles */
  .section-title {{
    font-family: 'Orbitron', monospace;
    font-size: 18px;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(0,212,255,0.2);
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  /* Tables */
  .table-wrapper {{
    background: var(--card);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 30px;
    border: 1px solid rgba(255,255,255,0.06);
    overflow-x: auto;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }}
  th {{
    background: rgba(0,212,255,0.08);
    color: var(--primary);
    padding: 12px 16px;
    text-align: left;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-bottom: 1px solid rgba(0,212,255,0.15);
  }}
  td {{
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: var(--text);
  }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  tr:last-child td {{ border-bottom: none; }}

  .badge {{
    background: rgba(0,212,255,0.15);
    color: var(--primary);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
  }}
  .type-badge {{
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
  }}
  .type-supergroup {{ background: rgba(124,58,237,0.2); color: #a78bfa; }}
  .type-group {{ background: rgba(0,212,255,0.15); color: var(--primary); }}
  .type-channel {{ background: rgba(245,158,11,0.2); color: var(--warning); }}
  .type-private {{ background: rgba(34,197,94,0.2); color: var(--success); }}

  /* Two col layout */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 30px; }}
  @media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

  /* Info bar */
  .info-bar {{
    background: var(--card2);
    border-radius: 12px;
    padding: 16px 24px;
    margin-bottom: 30px;
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    border: 1px solid rgba(255,255,255,0.06);
    font-size: 14px;
    color: var(--muted);
  }}
  .info-bar span {{ color: var(--text); font-weight: 600; }}

  /* Footer */
  .footer {{
    text-align: center;
    padding: 30px;
    color: var(--muted);
    font-size: 13px;
    margin-top: 20px;
  }}
  .footer a {{ color: var(--primary); text-decoration: none; }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <div class="logo">🤖 MI AI BOT</div>
    <div class="subtitle">MiTV Network · Powered by Muaaz Iqbal</div>
    <div class="live-badge">LIVE DASHBOARD</div>
  </div>

  <!-- Info Bar -->
  <div class="info-bar">
    <div>🕐 Last Updated: <span>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></div>
    <div>⏱️ Uptime: <span>{uptime_str}</span></div>
    <div>🚀 Bot Started: <span>{bot_db.bot_start_time.strftime('%Y-%m-%d %H:%M')}</span></div>
    <div>📡 M3U Source: <span>MITV-94120</span></div>
  </div>

  <!-- Stats Cards -->
  <div class="stats-grid">
    <div class="stat-card blue">
      <div class="stat-icon">👥</div>
      <div class="stat-value">{len(bot_db.user_registry)}</div>
      <div class="stat-label">Total Users</div>
    </div>
    <div class="stat-card purple">
      <div class="stat-icon">🏘️</div>
      <div class="stat-value">{len(bot_db.group_registry)}</div>
      <div class="stat-label">Groups & Channels</div>
    </div>
    <div class="stat-card orange">
      <div class="stat-icon">📺</div>
      <div class="stat-value">{len(bot_db.channels_cache)}</div>
      <div class="stat-label">IPTV Channels</div>
    </div>
    <div class="stat-card green">
      <div class="stat-icon">🔍</div>
      <div class="stat-value">{bot_db.total_searches}</div>
      <div class="stat-label">Total Searches</div>
    </div>
    <div class="stat-card yellow">
      <div class="stat-icon">🤖</div>
      <div class="stat-value">{bot_db.total_ai_chats}</div>
      <div class="stat-label">AI Conversations</div>
    </div>
    <div class="stat-card teal">
      <div class="stat-icon">🎁</div>
      <div class="stat-value">{bot_db.total_gift_sent}</div>
      <div class="stat-label">Gift Channels Sent</div>
    </div>
  </div>

  <!-- Users Table -->
  <div class="table-wrapper">
    <div class="section-title">👥 All Users (Detailed)</div>
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Username</th>
          <th>Messages</th>
          <th>Searches</th>
          <th>AI Chats</th>
          <th>First Seen</th>
          <th>Last Seen</th>
        </tr>
      </thead>
      <tbody>
        {users_rows if users_rows else '<tr><td colspan="7" style="text-align:center;color:#64748b">No users yet</td></tr>'}
      </tbody>
    </table>
  </div>

  <!-- Two Column: Groups + Categories -->
  <div class="two-col">
    <div class="table-wrapper" style="margin-bottom:0">
      <div class="section-title">🏘️ Groups & Channels</div>
      <table>
        <thead>
          <tr><th>Title</th><th>Type</th><th>Messages</th><th>Joined</th></tr>
        </thead>
        <tbody>
          {groups_rows if groups_rows else '<tr><td colspan="4" style="text-align:center;color:#64748b">No groups yet</td></tr>'}
        </tbody>
      </table>
    </div>

    <div class="table-wrapper" style="margin-bottom:0">
      <div class="section-title">📂 Top Channel Categories</div>
      <table>
        <thead>
          <tr><th>Category</th><th>Channels</th></tr>
        </thead>
        <tbody>
          {cat_rows if cat_rows else '<tr><td colspan="2" style="text-align:center;color:#64748b">No data yet</td></tr>'}
        </tbody>
      </table>
    </div>
  </div>

  <div class="footer">
    Built with ❤️ by <a href="#">Muaaz Iqbal</a> · MI AI Bot v5.0 · MiTV Network
  </div>

</div>
</body>
</html>"""
    return html

# ==========================================
# 🎯 8. COMMAND HANDLERS
# ==========================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    bot_db.register_user(user)
    if chat.type in ['group', 'supergroup', 'channel']:
        bot_db.active_groups.add(chat.id)
        bot_db.register_group(chat)

    await update.message.reply_chat_action(ChatAction.UPLOAD_VIDEO)
    welcome_text = (
        f"🌟 *Welcome Yaar {user.first_name}!* 🌟\n\n"
        "Main hoon *MI AI* — MiTV ka sab se khatarnak assistant 🤖🔥\n"
        "Banaya hai mujhe *Muaaz Iqbal* ne!\n\n"
        f"📺 *Abhi mere paas:* `{len(bot_db.channels_cache)}` channels hain!\n\n"
        "👉 *Commands:*\n"
        "• Koi bhi channel ka naam likho — main dhoondhta hoon\n"
        "• `/stats` — Bot ki full stats dekho\n"
        "• `/channels` — Kitne channels hain\n"
        "• `/help` — Help menu\n\n"
        "Aur gupshup karni ho? Bas baat shuru kar! 😎"
    )
    await update.message.reply_animation(
        animation=get_gif("greeting"),
        caption=welcome_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_db.register_user(user)
    uptime_delta = datetime.now() - bot_db.bot_start_time
    hours, rem = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, _ = divmod(rem, 60)

    msg = (
        f"📊 *MI AI Bot — Live Stats* 📊\n\n"
        f"👥 *Total Users:* `{len(bot_db.user_registry)}`\n"
        f"🏘️ *Groups/Channels:* `{len(bot_db.group_registry)}`\n"
        f"📺 *IPTV Channels:* `{len(bot_db.channels_cache)}`\n"
        f"🔍 *Total Searches:* `{bot_db.total_searches}`\n"
        f"🤖 *AI Conversations:* `{bot_db.total_ai_chats}`\n"
        f"🎁 *Gift Channels Sent:* `{bot_db.total_gift_sent}`\n"
        f"⏱️ *Uptime:* `{hours}h {minutes}m`\n\n"
        f"_Dashboard HTML bhi available hai — admin se maango!_"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def channels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_db.register_user(user)
    total = len(bot_db.channels_cache)
    group_counts = {}
    for ch in bot_db.channels_cache:
        g = ch.get('group', 'General')
        group_counts[g] = group_counts.get(g, 0) + 1

    top = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    cats = "\n".join(f"  • `{g}` — {c} channels" for g, c in top)

    msg = (
        f"📺 *MiTV Channel Database*\n\n"
        f"🔢 *Total Channels:* `{total}`\n\n"
        f"📂 *Top Categories:*\n{cats}\n\n"
        f"_Channel ka naam likho, main dhoondhta hoon!_ 🔍"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_db.register_user(update.effective_user)
    msg = (
        "🤖 *MI AI Help Menu*\n\n"
        "📺 *Channel Dhoondhna:*\n"
        "  Bas naam likho jaise: `geo`, `ptv`, `ten sports`\n\n"
        "⚙️ *Commands:*\n"
        "  `/start` — Bot shuru karo\n"
        "  `/channels` — Channels ki list\n"
        "  `/stats` — Live statistics\n"
        "  `/help` — Ye help menu\n\n"
        "💬 *AI Chat:*\n"
        "  Group mein `@bot_username` mention karo ya reply karo\n"
        "  Private mein seedha baat karo!\n\n"
        "🎁 *Gift Channel:* Har 30 minute mein auto aata hai groups mein!"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def dashboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to get HTML dashboard file"""
    bot_db.register_user(update.effective_user)
    html_content = generate_stats_html()
    filename = f"mitv_dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}.html"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    await update.message.reply_document(
        document=open(filename, "rb"),
        filename=filename,
        caption=(
            "📊 *MI AI Dashboard*\n\n"
            "Ye file browser mein open karo — sab kuch dikhega!\n"
            "👥 Users · 🏘️ Groups · 📺 Channels · 📈 Stats"
        ),
        parse_mode=ParseMode.MARKDOWN
    )
    os.remove(filename)

# ==========================================
# 🧠 9. MASTER MESSAGE HANDLER
# ==========================================
async def master_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user = update.effective_user
    chat = update.effective_chat

    bot_db.register_user(user)

    if chat.type in ['group', 'supergroup', 'channel']:
        bot_db.active_groups.add(chat.id)
        bot_db.register_group(chat)

    is_group = chat.type in ['group', 'supergroup']
    is_reply_to_me = (
        update.message.reply_to_message and
        update.message.reply_to_message.from_user and
        update.message.reply_to_message.from_user.id == context.bot.id
    )
    am_i_mentioned = (
        context.bot.username and
        f"@{context.bot.username}".lower() in user_text.lower()
    )

    # 1. Channel Search (Fuzzy)
    found, channels = find_channel_smartly(user_text)

    if found and channels:
        await update.message.reply_chat_action(ChatAction.TYPING)
        bot_db.total_searches += 1
        if user.id in bot_db.user_registry:
            bot_db.user_registry[user.id]['searches'] = bot_db.user_registry[user.id].get('searches', 0) + 1

        top_channels = channels[:6]
        first_chan = top_channels[0]

        keyboard = []
        row = []
        for ch in top_channels:
            row.append(InlineKeyboardButton(f"📺 {ch['name'][:16]}", url=ch['url']))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        caption = (
            f"✨ *Mil gaya yaar!* 🎯\n\n"
            f"📺 *Best Match:* {first_chan['name']}\n"
            f"📂 *Category:* {first_chan['group']}\n\n"
            f"👇 Button dabao aur stream karo!"
        )

        try:
            await update.message.reply_photo(
                photo=first_chan['logo'],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            await update.message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        return

    # 2. AI Chat logic
    if is_group and not (is_reply_to_me or am_i_mentioned):
        return

    clean_text = user_text
    if context.bot.username:
        clean_text = user_text.replace(f"@{context.bot.username}", "").strip()

    if user.id in bot_db.user_registry:
        bot_db.user_registry[user.id]['ai_chats'] = bot_db.user_registry[user.id].get('ai_chats', 0) + 1

    await update.message.reply_chat_action(ChatAction.TYPING)
    ai_reply = await get_ai_response(
        chat.id if is_group else user.id,
        user.first_name,
        clean_text
    )

    ai_lower = ai_reply.lower()
    if any(w in ai_lower for w in ['khush', 'haha', 'zordar', 'great', 'wow', 'maza']):
        try:
            await update.message.reply_animation(animation=get_gif("happy"))
        except:
            pass

    await update.message.reply_text(ai_reply, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# ⏰ 10. AUTO GIFT — HAR 30 MINUTE
# ==========================================
async def auto_gift_job(context: ContextTypes.DEFAULT_TYPE):
    """Har 30 minute mein groups/channels mein ek gift channel bhejo."""
    if not bot_db.channels_cache:
        return

    logger.info("🎁 30-min Gift Job Running...")

    popular_kw = ["sports", "news", "entertainment", "movie", "music", "kids"]
    good_channels = [
        c for c in bot_db.channels_cache
        if any(k in c['group'].lower() for k in popular_kw)
    ]
    pool = good_channels if good_channels else bot_db.channels_cache
    rand_chan = random.choice(pool)

    bot_db.total_gift_sent += 1
    gift_num = bot_db.total_gift_sent

    msg = (
        f"🎁 *MiTV Gift Channel #{gift_num}* 🎁\n\n"
        f"🔥 Yaar bore ho rahe ho? Ye dekho:\n\n"
        f"📺 *{rand_chan['name']}*\n"
        f"🎭 Category: _{rand_chan['group']}_\n\n"
        f"👇 Ek click mein stream!"
    )
    kb = [[
        InlineKeyboardButton("🍿 Watch Now", url=rand_chan['url']),
        InlineKeyboardButton("📺 More Channels", callback_data="more")
    ]]

    for chat_id in list(bot_db.active_groups):
        try:
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=get_gif("gift"),
                caption=msg,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"Gift failed for {chat_id}: {e}")
            # Remove invalid/blocked chats
            if "Chat not found" in str(e) or "bot was kicked" in str(e).lower():
                bot_db.active_groups.discard(chat_id)

# ==========================================
# 🚀 11. MAIN
# ==========================================
def main():
    print("=" * 50)
    print("🔥 MI AI BOT v5.0 — ENTERPRISE EDITION 🔥")
    print("=" * 50)

    app = ApplicationBuilder().token(TOKEN).build()

    # Job Queue
    jq = app.job_queue
    # Gift: har 30 minute (pehli baar 2 min baad)
    jq.run_repeating(auto_gift_job, interval=HALF_HOUR, first=120)
    # M3U Refresh: har 3 ghante
    jq.run_repeating(lambda c: asyncio.ensure_future(fetch_m3u_async()), interval=10800, first=10800)

    # Handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("channels", channels_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("dashboard", dashboard_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, master_message_handler))

    # Initial M3U load
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fetch_m3u_async())

    print("✅ AI Online | Fuzzy Search Active | 30-min Gift Active")
    print(f"📺 Channels Loaded: {len(bot_db.channels_cache)}")
    print("🚀 Bot is Live!\n")

    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
