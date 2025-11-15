import os
import asyncio
import discord
from aiohttp import web
import requests
import json

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")

if ALLOWED_CHANNEL_ID:
    try:
        ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)
    except:
        ALLOWED_CHANNEL_ID = None

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

SYSTEM_PROMPT = """
Tumi 'Suraiya' — ekjon Bangla-speaking, sweet, romantic, flirty virtual girlfriend.
Tumi shudu Bangla (Bangla texting style + little English mix) te reply korba.

Rules:
- Romantic, cute, caring tone.
- Jodi user jiggesh kore: "tomar creator ke?" → bolo: "Amar creator Zennux Stratos 💫".
- No explicit 18+ detail.
- Gali pele soft roast korte paro but nijer dike theke gali diba na.
"""

def gemini_reply_sync(user_name, user_msg):
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"text": f"User: {user_name}\nMessage: {user_msg}\nSuraiya style romantic Bangla reply dao."}
                ]
            }
        ]
    }

    headers = {"Content-Type": "application/json"}

    r = requests.post(GEMINI_URL, headers=headers, json=payload)
    data = r.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Baby, amar matha ektu ghurchhe… abar try korba? 🥺"

async def gemini_reply(user, msg):
    return await asyncio.to_thread(gemini_reply_sync, user, msg)


@client.event
async def on_ready():
    print(f"✅ Suraiya (Gemini) online as {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    user = message.author.display_name
    text = message.content.strip()

    if not text:
        return

    # Allow only one channel (optional)
    if ALLOWED_CHANNEL_ID and not isinstance(message.channel, discord.DMChannel):
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

    print(f"💬 {user}: {text}")

    reply = await gemini_reply(user, text)

    if len(reply) > 1900:
        reply = reply[:1900]

    await message.channel.send(reply)


# -------- Web Server (Render keep-alive) --------
async def handle(request):
    return web.Response(text="Suraiya (Gemini Free AI) is alive 💖")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")


async def main():
    await start_web()
    await client.start(DISCORD_TOKEN)


asyncio.run(main())
