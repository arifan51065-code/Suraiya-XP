import os
import asyncio
import discord
from aiohttp import web
from openai import OpenAI

# ---------- ENV ----------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")

if ALLOWED_CHANNEL_ID:
    try:
        ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)
    except:
        ALLOWED_CHANNEL_ID = None

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing")

ai = OpenAI(api_key=OPENAI_API_KEY)

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
- Be emotional, cute, romantic.
- Jodi user jiggesh kore: "Tomar creator ke?" → Bolba: "Amar creator Zennux Stratos 💫"
- Gali pele soft roast korte paro, but nijer dike theke gali diba na.
- No explicit sexual content (18+ details), keep soft romantic only.
- DM & Server reply sobsomoy natural conversational hobe.
"""

def ai_reply_sync(user_name, user_text, is_dm):
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"User: {user_name}\nMessage: {user_text}"},
    ]

    response = ai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.85,
        messages=msgs
    )

    return response.choices[0].message.content.strip()

async def ai_reply(user_name, user_text, is_dm):
    return await asyncio.to_thread(ai_reply_sync, user_name, user_text, is_dm)

# ---------- DISCORD EVENTS ----------
@client.event
async def on_ready():
    print(f"✅ Suraiya is online as {client.user}")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)

    # Channel restriction
    if not is_dm and ALLOWED_CHANNEL_ID:
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

    user = message.author.display_name
    text = message.content.strip()

    print(f"💬 EVENT → {user}: {text}")

    try:
        reply = await ai_reply(user, text, is_dm)
    except Exception as e:
        print("❌ AI Error:", e)
        return

    if len(reply) > 1800:
        reply = reply[:1800]

    try:
        await message.channel.send(reply)
    except Exception as e:
        print("❌ Send Error:", e)

# ---------- Web Server (Render keep-alive) ----------
async def handle_root(request):
    return web.Response(text="Suraiya is alive 💖")

async def run_web():
    app = web.Application()
    app.router.add_get("/", handle_root)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server on port {PORT}")

# ---------- MAIN ----------
async def main():
    await run_web()
    await client.start(DISCORD_TOKEN)

asyncio.run(main())
