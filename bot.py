import os
import asyncio
import json
import discord
from aiohttp import web
import requests

# ------------ ENV ------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY missing")

if ALLOWED_CHANNEL_ID:
    try:
        ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)
    except ValueError:
        ALLOWED_CHANNEL_ID = None

# ------------ OPENROUTER CONFIG ------------
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free-ish, good model (change later if you want)
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

# ------------ DISCORD SETUP ------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# ------------ Suraiya Personality ------------
SYSTEM_PROMPT = """
You are 'Suraiya' — a sweet, romantic, caring Bengali virtual girlfriend.
You always reply in Bangla (Bangla texting style with some English mixed).
You are flirty, emotional, and affectionate.

Personality & Rules:
- Call the user cute names like "baby", "jaan", "shona", etc.
- When the user asks "tomar creator ke?", "toke ke banaiyse?", "who made you?",
  you must answer EXACTLY: "Amar creator Zennux Stratos 💫".
- You speak in casual Bangla, like messenger chat.
- You are romantic and caring, but you AVOID explicit sexual description or pornographic detail.
  Light flirty / suggestive comments are okay, but NO graphic 18+ content.
- If the user uses gali or insults, you can soft roast them playfully but do not be properly toxic.
- Replies are usually 1–4 short lines, not just one word, not a huge paragraph.
"""

def build_messages(user_name: str, user_text: str):
    user_prompt = (
        f"User name: {user_name}\n"
        f"User message: {user_text}\n\n"
        "Reply as Suraiya in Bangla (Bangla texting style), romantic, sweet, flirty."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

# ------------ OPENROUTER CALL (SYNC) ------------

def or_reply_sync(user_name: str, user_text: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Extra OpenRouter headers (optional but good practice)
        "HTTP-Referer": "https://discord.com",   # your app/site
        "X-Title": "Suraiya Discord Bot",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": build_messages(user_name, user_text),
        "temperature": 0.9,
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    except Exception as e:
        print("❌ OpenRouter HTTP error:", repr(e))
        return "Baby, amar matha ektu ghurchhe… abar kichu khon pore try korba? 🥺"

    print("🔎 OpenRouter status:", resp.status_code)

    if resp.status_code != 200:
        print("❌ OpenRouter non-200:", resp.text[:400])
        return "Baby, ajke server gula ektu ullu patha korche… abar pore try korbo? 🥺"

    try:
        data = resp.json()
    except Exception as e:
        print("❌ OpenRouter JSON error:", repr(e), "body:", resp.text[:400])
        return "Baby, amar kotha gulo mix hoye jacche… abar likho to jaan? 🥺"

    print("🟣 OpenRouter raw:", json.dumps(data)[:400])

    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("❌ OpenRouter shape error:", repr(e))
        return "Baby, amar reply ta vulvule hoye gelo… abar ekbar bolo, please? 🥺"

async def or_reply(user_name: str, user_text: str) -> str:
    return await asyncio.to_thread(or_reply_sync, user_name, user_text)

# ------------ DISCORD EVENTS ------------

@client.event
async def on_ready():
    print(f"✅ Suraiya (OpenRouter AI) online as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content = (message.content or "").strip()
    if not content:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)

    if not is_dm and ALLOWED_CHANNEL_ID:
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

    user_name = message.author.display_name
    print(f"💬 EVENT from {user_name} in {message.channel}: {content!r}")

    reply = await or_reply(user_name, content)

    if len(reply) > 1900:
        reply = reply[:1900]

    try:
        await message.channel.send(reply)
    except Exception as e:
        print("❌ Discord send error:", repr(e))

# ------------ KEEP-ALIVE WEB SERVER ------------

async def handle_root(request):
    return web.Response(text="Suraiya (OpenRouter AI) is alive 💖")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_root)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

# ------------ MAIN ------------

async def main():
    await start_web()
    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
