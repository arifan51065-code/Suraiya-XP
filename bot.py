import os
import discord
from dotenv import load_dotenv

# .env or Render env theke token
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message: discord.Message):
    # nijer message ignore
    if message.author.bot:
        return

    # debug print – Render log e dekhbo
    print(f"💬 Got message from {message.author} in {message.channel}: {message.content!r}")

    try:
        await message.channel.send(f"Test reply, {message.author.display_name} ❤️")
    except Exception as e:
        print(f"❌ Send error: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing")
    client.run(DISCORD_TOKEN)
