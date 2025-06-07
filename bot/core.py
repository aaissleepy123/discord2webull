import os
import time
import logging
from datetime import datetime
from discord.ext import commands
from discord import Intents, Message

from dotenv import load_dotenv
from bot.ocr import ocr_from_screenshot
from bot.parser import parse_message
from bot.trading import handle_trade,MarketOrderExecutor


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
async def on_message(message):
    trades = parse_message(message.content)
    executor = MarketOrderExecutor(trades)  # Pass the bot reference

    for trade in trades:
        try:
            await executor.execute_from_parser(trade)
        except Exception as e:
            print(f"Trade failed: {e}")

    # Process attachments (screenshots) if needed
    for attachment in message.attachments:
        if attachment.content_type.startswith('image'):
            text = ocr_from_screenshot(await attachment.read())
            trades = parse_message(text)
            for trade in trades:
                await executor.execute_from_parser(trade)

def start_bot():
    bot.run(DISCORD_TOKEN)

