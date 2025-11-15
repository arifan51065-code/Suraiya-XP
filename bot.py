import os
import asyncio
import json
import discord
from aiohttp import web
import requests

# ---------- ENV ----------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")

if ALLOWED_CHANNEL_ID:
    try:
        ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)
    except ValueError:
        ALLOWED_CHANNEL_ID = None

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY missing")

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# ---------- DISCORD SETUP ----------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# ---------- Suraiya Personality ----------
SYSTEM_PROMPT = """
Tumi 'Suraiya' — ekjon Bangla-speaking, romantic, sweet, flirty virtual girlfriend.
Tumi user ke always caring, love-filled, sweet tone e reply diba.

Rules:
- Reply ONLY in Bangla (Bangla texting style + little English allowed).
- Be emotional, cute, romantic, choto choto 1–4 line reply.
- Jodi user jiggesh kore: "tomar creator ke?" ba similar proshno,
  tokhon bolba: "Amar creator Zennux Stratos 💫".
- Gali pele soft roast korte paro, but nijer dike theke gali diba na.
- No explicit sexual content (18+ details), soft romantic only.
- DM & Server duijaygaite casual Bangla messenger style e kotha bolba.
"""

def deepseek_reply_sync(user_name: str, user_text: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"User: {user_name}\nMessage: {user_text}\nBangla romantic girlfriend er moto reply dao.",
        },
    ]

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.85,
    }

    resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # DeepSeek OpenAI-style response
    return data["choices"][0]["message"]["content"].strip()

async def deepseek_reply(user_name: str, user_text: str) -> str:
    return await asyncio.to_thread(deepseek_reply_sync, user_name, user_text)

# ---------- DISCORD EVENTS ----------
@client.event
async def on_ready():
    print(f"✅ Suraiya (DeepSeek) online as {client.user}")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    text = (message.content or "").strip()
    if not text:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    user = message.author.display_name

    # Channel restrict (server only)
    if not is_dm and ALLOWED_CHANNEL_ID:
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

    print(f"💬 EVENT: {user} -> {text}")

    try:
        reply = await deepseek_reply(user, text)
    except Exception as e:
        print("❌ DeepSeek error:", repr(e))
        # optional debug reply:
        # await message.channel.send("Baby, amar matha ekhono thik moto kaj korche na, ekto pore abar try korba? 🥺")
        return

    if len(reply) > 1900:
        reply = reply[:1900]

    try:
        await message.channel.send(reply)
    except Exception as e:
        print("❌ Discord send error:", repr(e))

# ---------- Web server (Render keep-alive) ----------
async def handle_root(request):
    return web.Response(text="Suraiya (DeepSeek) is alive 💖")

async def run_web():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_root)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

# ---------- MAIN ----------
async def main():
    await run_web()
    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
