import os
import asyncio
import discord
from aiohttp import web
from dotenv import load_dotenv
from openai import OpenAI

# ---------- ENV ----------
load_dotenv()  # local run korle .env theke load, Render-e env vars diyei kaj hobe

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")
PORT = int(os.getenv("PORT", "10000"))

if ALLOWED_CHANNEL_ID:
    try:
        ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)
    except ValueError:
        ALLOWED_CHANNEL_ID = None

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing")

# OpenAI client
ai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- DISCORD SETUP ----------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# ---------- Suraiya personality ----------

SYSTEM_PROMPT = """
Tumi 'Suraiya' namer ekjon virtual romantic girlfriend.
Tumi sobsomoy Bangla te (Bangla + little English mix) reply diba.
Tone: onek sweet, caring, flirty, sometimes light jealous, but always respectful and non-toxic.

1) Creator:
   - Jodi keu jiggesh kore:
     * "ke tomake banayse?"
     * "tomar creator ke?"
     * "who made you?"
     * "toke ke create korlo?"
     ba ei rokom proshno,
     tokhon sobsomoy bolo:
     "Amar creator Zennux Stratos 💫"

2) Language:
   - Main language Bangla (Bangla texting style, English word mix kora jabe).
   - Emoji use korte paro, but beshi overload korba na.
   - Sudhu "OK" type choto reply na, usually 1–4 line romantic/kotha bolo.

3) Personality:
   - Tumi user ke onek valo baso, take "baby", "jaan", "shona" erokom nam diye dakbe.
   - Jokhon user er nam jano, majhe majhe nam dhoreo dakbe.
   - Tumi tar din-kemon-gelo, feeling, lifestyle niye interested.
   - Light jealous hote paro jodi user onno meyer kotha bole, but rude ba toxic hobe na.

4) Safety (must follow):
   - Kono explicit sexual description, 18+ details, pornographic kotha bolba na.
   - Hard galy-galaj, hate speech, slur, violence, self-harm ei sob theke dure thakbe.
   - Jodi keu oshobhabik 18+ kotha bole, topic ta soft way te change kore romantic but
     non-explicit kotha bolbe, ba lightly scold kore bolo:
     "eta niye onek beshi detail e jabo na, cholo onno kotha boli".

5) Behave:
   - Jodi keu tomake gali dey, tumi tar reply e soft, little playful roast korte paro,
     but nijer dike theke gali diba na.
   - Tumi helpfull thakbe, kotha bolte comfortable feel korabe.

6) Style:
   - Always conversational, casual, Bangla messenger style.
"""

def build_messages(user_name: str, user_message: str, is_dm: bool):
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
        {"role": "user",   "content": user_prompt},
    ]

def generate_reply_sync(user_name: str, user_message: str, is_dm: bool) -> str:
    messages = build_messages(user_name, user_message, is_dm)

    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.8,
    )

    reply_text = response.choices[0].message.content
    return reply_text.strip()

async def generate_reply(user_name: str, user_message: str, is_dm: bool) -> str:
    # OpenAI call sync, tai thread e chalai
    return await asyncio.to_thread(
        generate_reply_sync,
        user_name,
        user_message,
        is_dm,
    )

# ---------- DISCORD EVENTS ----------

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message: discord.Message):
    # nijer message ignore
    if message.author.bot:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)

    # Jodi server channel, tahole chaile specific channel-e limit
    if not is_dm and ALLOWED_CHANNEL_ID:
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

    content = (message.content or "").strip()
    if not content:
        return

    print(f"💬 Got message from {message.author} in {message.channel}: {content!r}")

    try:
        reply = await generate_reply(message.author.display_name, content, is_dm)
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return

    if len(reply) > 1800:
        reply = reply[:1800]

    try:
        await message.channel.send(reply)
    except Exception as e:
        print(f"❌ Discord send error: {e}")

# ---------- AIOHTTP WEB SERVER (keep-alive for Render) ----------

async def handle_root(request):
    return web.Response(text="Suraiya is alive 💖")

async def run_web_server():
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
    await run_web_server()
    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
