import os
import asyncio
import json
import discord
from aiohttp import web
import requests

# ------------ ENV ------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")
if not HF_API_KEY:
    raise RuntimeError("HUGGINGFACE_API_KEY missing")

if ALLOWED_CHANNEL_ID:
    try:
        ALLOWED_CHANNEL_ID = int(ALLOWED_CHANNEL_ID)
    except ValueError:
        ALLOWED_CHANNEL_ID = None

# ------------ HUGGINGFACE MODEL CONFIG ------------
# Safe, instruct model (real AI, free)
HF_MODEL = "microsoft/Phi-3-mini-4k-instruct"
HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

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
- No explicit 18+ details. Soft romantic thakbe, but explicit sexual description diba na.
- Gali pele soft roast korte paro, but nijer dike theke hard gali diba na.
- DM & server duijaygaite casual Bangla messenger style e kotha bolba.
- Always behave respectful and safe.
"""

def build_prompt(user_name: str, user_text: str) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"User name: {user_name}\n"
        f"User message: {user_text}\n\n"
        "Suraiya hisebe Bangla romantic, sweet, flirty style e reply dao."
    )

# ------------ HF CALL (SYNC) ------------

def hf_reply_sync(user_name: str, user_text: str) -> str:
    prompt = build_prompt(user_name, user_text)

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 180,
            "temperature": 0.9,
            "top_p": 0.9,
        }
    }

    try:
        resp = requests.post(HF_URL, headers=headers, json=payload, timeout=60)
    except Exception as e:
        print("❌ HF HTTP error:", repr(e))
        return "Baby, amar matha ektu ghurchhe… abar kichu khon pore try korba? 🥺"

    print("🔎 HF status:", resp.status_code)

    if resp.status_code != 200:
        print("❌ HF non-200:", resp.text[:400])
        return "Baby, ajke amar network ta ektu off lagche… abar pore try korbo, thik ache? 🥺"

    try:
        data = resp.json()
    except Exception as e:
        print("❌ HF JSON error:", repr(e), "body:", resp.text[:400])
        return "Baby, amar kotha gulo mix hoye jacche… abar ekbar likho to jaan? 🥺"

    print("🟣 HF raw:", json.dumps(data)[:300])

    # Normal text-generation format: list with "generated_text"
    try:
        if isinstance(data, list) and "generated_text" in data[0]:
            full = data[0]["generated_text"]
            # generated_text = prompt + completion → promptটা কেটে ফেলি
            generated = full[len(prompt):].strip()
            return generated or full.strip()

        # Some pipelines may directly return text
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"].strip()

        # Fallback: stringify
        return str(data)
    except Exception as e:
        print("❌ HF shape error:", repr(e))
        return "Baby, amar reply ta vulvule hoye gelo… abar ekbar bolo, please? 🥺"

async def hf_reply(user_name: str, user_text: str) -> str:
    return await asyncio.to_thread(hf_reply_sync, user_name, user_text)

# ------------ DISCORD EVENTS ------------

@client.event
async def on_ready():
    print(f"✅ Suraiya (HF AI) online as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content = (message.content or "").strip()
    if not content:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)

    # optional channel restriction
    if not is_dm and ALLOWED_CHANNEL_ID:
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

    user_name = message.author.display_name
    print(f"💬 EVENT from {user_name} in {message.channel}: {content!r}")

    reply = await hf_reply(user_name, content)

    if len(reply) > 1900:
        reply = reply[:1900]

    try:
        await message.channel.send(reply)
    except Exception as e:
        print("❌ Discord send error:", repr(e))

# ------------ KEEP-ALIVE WEB SERVER ------------

async def handle_root(request):
    return web.Response(text="Suraiya (HuggingFace AI) is alive 💖")

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
