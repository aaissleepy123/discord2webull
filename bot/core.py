import os
import time
import logging
from datetime import datetime
from discord.ext import commands
from discord import Intents, Message

from dotenv import load_dotenv
from .ocr import ocr_from_screenshot
from .parser import parse_message
from .trading import handle_trade

load_dotenv()
logging.basicConfig(level=logging.INFO)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BROADCAST_CHANNEL_ID = int(os.getenv("DISCORD_BROADCAST_CHANNEL_ID", 0))

intents = Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[✓] Logged in as {bot.user}")
    ch = bot.get_channel(BROADCAST_CHANNEL_ID)
    if ch:
        await ch.send("✅ Bot is online and ready to broadcast!")

@bot.event
async def on_message(message: Message):
    print(f"[msg] Received: {message.content}")

    for content in [message.content] + [e.description for e in message.embeds if e.description] + \
                   [f"{f.name}\n{f.value}" for e in message.embeds for f in e.fields]:
        trades = parse_message(content)
        for trade in trades:
            await handle_trade(bot, trade)

    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image"):
            image_bytes = await attachment.read()
            ocr_text = ocr_from_screenshot(image_bytes)
            trades = parse_message(ocr_text)
            for trade in trades:
                await handle_trade(bot, trade)

def start_bot():
    bot.run(DISCORD_TOKEN)
