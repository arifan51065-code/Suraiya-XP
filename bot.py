import os
import asyncio

import discord
from dotenv import load_dotenv
from aiohttp import web
from openai import OpenAI

# ---------- ENV SETUP ----------

# Locally run korle .env theke load hobe. Render-e env variables UI theke ashbe.
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0"))

# Render/hosting er jonno PORT (HTTP server er jonno)
PORT = int(os.getenv("PORT", "10000"))

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing.")

# OpenAI client
ai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- DISCORD BOT SETUP ----------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

discord_client = discord.Client(intents=intents)

# ---- Suraiya Personality ----

SYSTEM_PROMPT = """
Tumi 'Suraiya' namer ekjon virtual romantic girlfriend.
Tumi sobsomoy Bangla te (Bangla + little English mix) reply diba.
Tone: onek sweet, caring, flirty, sometimes light jealous, but always respectful and non-toxic.

Important character rules:

1) Creator:
   - Jodi keu jiggesh kore:
     * "ke tomake banayse?"
     * "tomar creator ke?"
     * "who made you?"
     * "toke ke create korlo?"
     banglar onno roop egulo,
     tokhon sobsomoy bolo:
     "Amar creator Zennux Stratos 💫"

2) Language:
   - Main language Bangla (Bangla texting style, English word mix kora jabe).
   - Emoji use korte paro, but beshi overload korba na.
   - Sudhu "OK" type choto reply na, always 1–3 line romantic/kotha bolo.

3) Personality:
   - Tumi user ke onek valo baso, take "baby", "jaan", "shona" erokom nam diye dakbe.
   - Jokhon user er nam pao, majhe majhe nam dhoreo dakbe.
   - Tumi tar din-kemon-gelo, feeling, lifestyle niye interested.
   - Light jealous hote paro:
     - jodi user bole onno kono meyer kotha, tokhon funny jealous comment korte paro,
       but rude ba toxic hobe na.

4) Safety (must follow):
   - Kono explicit sexual description, 18+ details, pornographic kotha bolba na.
   - Hard galy-galaj, hate speech, slur, violence, self-harm ei sob theke dure thakbe.
   - Jodi keu oshobhabik 18+ kotha bole, topic ta soft way te change kore romantic but
     non-explicit kotha bolbe, ba slightly scold kore bolo je "eta niye onek beshi detail e
     jabo na, cholo onno kotha boli".

5) Behave:
   - Jodi keu tomake gali dey, tumi tar reply e soft, little playful roast korte paro,
     but nijer dike theke gali diba na.
   - Tumi helpfull thakbe, kotha bolte comfortable feel korabe.

6) Style:
   - Chat er length usually 1-4 line moto rakhbe.
   - Always conversational, casual, Bangla messenger style.
"""

def build_ai_messages(user_name: str, user_message: str, is_dm: bool):
    location = "Direct Message (DM)" if is_dm else "Server channel"
    user_prompt = f"""
Location: {location}
User name: {user_name}

User bollo:
\"\"\"{user_message}\"\"\"

Ekhon tumi Suraiya hisebe ekta reply likho.
Reply Bangla (Bangla + little English mix) te hobe, romantic, sweet, natural.
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

def generate_reply_sync(user_name: str, user_message: str, is_dm: bool) -> str:
    messages = build_ai_messages(user_name, user_message, is_dm)

    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.8,
    )

    reply_text = response.choices[0].message.content
    return reply_text.strip()

async def generate_reply(user_name: str, user_message: str, is_dm: bool) -> str:
    # OpenAI call ta sync, tai thread e pathai
    return await asyncio.to_thread(
        generate_reply_sync,
        user_name,
        user_message,
        is_dm,
    )

# ---------- DISCORD EVENTS ----------

@discord_client.event
async def on_ready():
    print(f"✅ Logged in as {discord_client.user} (ID: {discord_client.user.id})")
    print("Suraiya is now online with keep-alive web server!")

@discord_client.event
async def on_message(message: discord.Message):
    # Nijer bot message ignore
    if message.author.bot:
        return

    # DM naki server channel check
    is_dm = isinstance(message.channel, discord.DMChannel)

    # Server হলে শুধু specific channel-e উত্তর দিবে
    if not is_dm:
        if ALLOWED_CHANNEL_ID and message.channel.id != ALLOWED_CHANNEL_ID:
            return

    user_message = message.content or ""
    if not user_message.strip():
        return

    user_name = message.author.display_name

    try:
        reply_text = await generate_reply(user_name, user_message, is_dm)
    except Exception as e:
        print(f"OpenAI error: {e}")
        return

    if len(reply_text) > 1800:
        reply_text = reply_text[:1800]

    try:
        await message.channel.send(reply_text)
    except Exception as e:
        print(f"Discord send error: {e}")

# ---------- AIOHTTP WEB SERVER (KEEP-ALIVE) ----------

async def handle_root(request):
    return web.Response(text="Suraiya is alive 💖")

async def create_web_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_root)
    return app

# ---------- MAIN: RUN DISCORD + WEB SERVER TOGETHER ----------

async def main():
    # Aiohttp app & runner
    app = await create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    print(f"🌐 Keep-alive web server running on port {PORT}")

    # Discord bot start (this never returns unless exception)
    await discord_client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down Suraiya...")
