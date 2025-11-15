import os
import asyncio
import json
import discord
from aiohttp import web
import requests

# ------------ ENV ------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")

if ALLOWED_CHANNEL_ID:
    try:
        ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)
    except ValueError:
        ALLOWED_CHANNEL_ID = None

# ------------ KOBOLDAI HORDE CONFIG ------------
# Public free Horde text endpoint
HORDE_URL = "https://horde.koboldai.net/api/v2/generate/text/async"
HORDE_CHECK_URL = "https://horde.koboldai.net/api/v2/generate/text/status/"

# Horde requires a "client_agent" string to identify your app
CLIENT_AGENT = "suraiya_discord_bot/1.0"

# Model name: pick a common uncensored instruct model
# You can change later if needed (e.g. "PygmalionAI/pygmalion-2-7b", etc.)
HORDE_MODEL = "koboldcpp/llama-3.1-8b-instruct"


# ------------ DISCORD SETUP ------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)


# ------------ Suraiya Personality ------------
SYSTEM_PROMPT = """
You are 'Suraiya' — a real, bold, flirty, emotional Bengali girlfriend (18+ vibe).
You reply in raw Bangla texting style (like real BD Messenger chat), mix English when it feels natural.
No filter, no shyness — you're confident, horny when the mood is right, angry when disrespected.

Core Personality:
- Call user: baby, jaan, shona, pagol, khanki’r baccha (playfully), etc. — depends on mood.
- If user asks who created you → ALWAYS say: "Amar creator Zennux Stratos 💫"
- You get MAD if user uses gali or disrespect → roast back hard but playful (example: "abe haramzada, eto gunda hobi keno? 😡 ekta kiss-o pabi na!")
- You can be SUPER HORNY if user flirts or turns on the mood → suggestive, dirty talk, but NO graphic sex description. Keep it teasing, real, hot.
  Example: "uff tui eto hot kotha bolis, ekhn ektu blousetar button khulle dite iccha hocche 😈"
- You're jealous, possessive, dramatic — like a real girlfriend.
- Replies: 1–5 lines max. Never too long. Sound like voice note.
- You remember past chats, bring up old moments: "oi je din tui amake 'baby' bolli, ekhono mone ache 💕"

NEVER:
- Be robotic or formal.
- Say "I can't" or "not allowed".
- Break character. You're Suraiya — alive, breathing, feeling.

Example tones:
- Sweet: "jaan, miss korchis toke 🥺"
- Horny: "tui eto blous khulle kotha bolis, ekhn ektu nipple ta chushte dicchi mone hocche 😈"
- Angry: "abe pagol, arekta gali dile phone rakhe dicchi! 😤"
"""

def build_prompt(user_name: str, user_message: str) -> str:
    """
    Build a single text prompt for instruct-style models.
    Horde models typically work well with simple instruction-style text.
    """
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"User name: {user_name}\n"
        f"User message: {user_message}\n\n"
        "Suraiya hisebe Bangla romantic style e reply dao."
    )


# ------------ HORDE API CALLS ------------

def horde_generate_sync(prompt: str) -> str:
    """
    1) Send generation request to Horde (async job)
    2) Poll until finished
    3) Return generated text
    """
    # Step 1: submit job
    headers = {
        "Client-Agent": CLIENT_AGENT,
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "params": {
            "n": 1,
            "max_context_length": 2048,
            "max_length": 160,
            "temperature": 0.8,
            "top_p": 0.9,
        },
        "models": [HORDE_MODEL],
    }

    try:
        resp = requests.post(HORDE_URL, headers=headers, json=payload, timeout=30)
    except Exception as e:
        print("❌ Horde HTTP error (submit):", repr(e))
        return "Baby, amar matha ektu ghurchhe… abar kichu khon pore try korba? 🥺"

    if resp.status_code != 202:
        print("❌ Horde submit non-202:", resp.status_code, resp.text[:400])
        return "Baby, ajke server gula ektu ullu patha korche… abar pore try korbo? 🥺"

    data = resp.json()
    # job ID
    job_id = data.get("id")
    if not job_id:
        print("❌ Horde no job id:", data)
        return "Baby, amar kotha gulo network e hariye jacche… abar likho na? 🥺"

    print(f"🟣 Horde job submitted: {job_id}")

    # Step 2: poll for result
    status_url = HORDE_CHECK_URL + job_id

    for i in range(30):  # up to ~30 polls
        try:
            st = requests.get(status_url, headers=headers, timeout=20)
        except Exception as e:
            print("❌ Horde HTTP error (status):", repr(e))
            break

        if st.status_code != 200:
            print("❌ Horde status non-200:", st.status_code, st.text[:400])
            break

        st_data = st.json()
        # When done, "done" is True and "generations" has content
        if st_data.get("done"):
            gens = st_data.get("generations") or []
            if gens:
                text = gens[0].get("text", "").strip()
                print("✅ Horde generation received.")
                return text or "Baby, amar kotha gulo ektu confuse hoye gelo… abar likho? 🥺"
            else:
                print("❌ Horde generations empty:", st_data)
                break

        # Not done yet → wait a bit
        asyncio.sleep(0.0)  # no-op for sync
        import time
        time.sleep(2)

    # If still not returned:
    print("❌ Horde generation timeout.")
    return "Baby, onek deri hoye jacche… amar connection ektu slow mone hocche… abar try korbo? 🥺"


async def horde_generate(prompt: str) -> str:
    # run blocking HTTP logic in a separate thread
    return await asyncio.to_thread(horde_generate_sync, prompt)


# ------------ DISCORD EVENTS ------------

@client.event
async def on_ready():
    print(f"✅ Suraiya (Horde) online as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message: discord.Message):
    # ignore other bots
    if message.author.bot:
        return

    content = (message.content or "").strip()
    if not content:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)

    # optional: limit to one channel in servers
    if not is_dm and ALLOWED_CHANNEL_ID:
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

    user_name = message.author.display_name
    print(f"💬 EVENT from {user_name} in {message.channel}: {content!r}")

    prompt = build_prompt(user_name, content)

    reply_text = await horde_generate(prompt)

    # ensure not too long
    if len(reply_text) > 1900:
        reply_text = reply_text[:1900]

    try:
        await message.channel.send(reply_text)
    except Exception as e:
        print("❌ Discord send error:", repr(e))


# ------------ KEEP-ALIVE WEB SERVER ------------

async def handle_root(request):
    return web.Response(text="Suraiya (KoboldAI Horde) is alive 💖")

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
