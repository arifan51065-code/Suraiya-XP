import os
import asyncio
import discord
from aiohttp import web

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# ---------- Discord events ----------

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message: discord.Message):
    # nijer message ignore
    if message.author.bot:
        return

    # DEBUG: ei line log e dekhte chabo
    print(f"💬 EVENT: from={message.author} channel={message.channel} content={message.content!r}")

    try:
        await message.channel.send(f"Test reply, {message.author.display_name} ✅")
    except Exception as e:
        print(f"❌ Send error: {e}")

# ---------- aiohttp web server for Render ----------

async def handle_root(request):
    return web.Response(text="Bot alive ✅")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_root)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

# ---------- main ----------

async def main():
    await run_web_server()
    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing")
    asyncio.run(main())
