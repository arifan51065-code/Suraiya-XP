import os
import asyncio
import json
import discord
from aiohttp import web
import requests

# ------------ ENV ------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing")

if ALLOWED_CHANNEL_ID:
    try:
        ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)
    except ValueError:
        ALLOWED_CHANNEL_ID = None

# Google Gemini endpoint (FREE model)
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-1.5-flash-latest:generateContent"
    f"?key={GEMINI_API_KEY}"
)

# ------------ DISCORD SETUP ------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# ------------ Suraiya Personality ------------
SYSTEM_PROMPT = """
Tumi 'Suraiya' — ekjon Bangla-speaking, sweet, romantic, flirty virtual girlfriend.
Tumi shudhu Bangla (Bangla texting style + little English mix) te reply korba.

Rules:
- Romantic, cute, caring tone, usually 1–4 line reply.
- Jodi user jiggesh kore: "tomar creator ke?" ba same type question,
  tokhon bolba: "Amar creator Zennux Stratos 💫".
- No explicit 18+ details. Soft romantic thakbe.
- Gali pele soft roast korte paro, but nijer dike theke hard gali diba na.
- DM & server duijaygaite casual Bangla messenger style e kotha bolba.
"""

# ------------ GEMINI CALL ------------

def gemini_reply_sync(user_name: str, user_msg: str) -> str:
    """Blocking HTTP call to Gemini; will run in thread."""
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {
                        "text": (
                            f"User: {user_name}\n"
                            f"Message: {user_msg}\n\n"
                            "Ekhon tumi Suraiya hisebe ekta "
                            "sweet romantic Bangla reply dao."
                        )
                    },
                ]
            }
        ]
    }

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=25)
    except Exception as e:
        print("❌ Gemini HTTP error:", repr(e))
        return "Baby, amar matha ektu ghurchhe… abar kichu khon pore try korba? 🥺"

    print("🔎 Gemini status:", resp.status_code)

    # If not OK, log body and return soft error text
    if resp.status_code != 200:
        text_preview = resp.text[:400]
        print("❌ Gemini non-200 response:", text_preview)
        return "Baby, ajke amar network ta ektu off lagche… abar ektu pore try korba? 🥺"

    try:
        data = resp.json()
    except Exception as e:
        print("❌ Gemini JSON parse error:", repr(e), "body:", resp.text[:400])
        return "Baby, amar matha ektu hang hoye gelo… abar chesta korbo, thik ache? 🥺"

    # Small debug preview
    print("🟣 Gemini raw:", json.dumps(data)[:400])

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print("❌ Gemini shape error:", repr(e))
        return "Baby, amar kotha gulo mix hoye jacche… tumi abar ektu likho na? 🥺"


async def gemini_reply(user_name: str, user_msg: str) -> str:
    """Async wrapper to call Gemini in a thread."""
    return await asyncio.to_thread(gemini_reply_sync, user_name, user_msg)

# ------------ DISCORD EVENTS ------------

@client.event
async def on_ready():
    print(f"✅ Suraiya (Gemini) online as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message: discord.Message):
    # ignore bots (including own)
    if message.author.bot:
        return

    content = (message.content or "").strip()
    if not content:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)

    # Channel restriction for server messages
    if not is_dm and ALLOWED_CHANNEL_ID:
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

    user_name = message.author.display_name
    print(f"💬 EVENT from {user_name} in {message.channel}: {content!r}")

    reply = await gemini_reply(user_name, content)

    if len(reply) > 1900:
        reply = reply[:1900]

    try:
        await message.channel.send(reply)
    except Exception as e:
        print("❌ Discord send error:", repr(e))

# ------------ KEEP-ALIVE WEB SERVER ------------

async def handle_root(request):
    return web.Response(text="Suraiya (Gemini) is alive 💖")

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
