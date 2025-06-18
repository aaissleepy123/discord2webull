import os
import time
import logging
from datetime import datetime
from discord.ext import commands
from discord import Intents, Message
import asyncio
import threading

from dotenv import load_dotenv
from bot.ocr import ocr_from_screenshot
from bot.parser import parse_message
from bot.trading import submit_trade

load_dotenv()
logging.basicConfig(level=logging.INFO)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BROADCAST_CHANNEL_ID = int(os.getenv("DISCORD_BROADCAST_CHANNEL_ID", 0))
AUTHORIZED_USER_ID = int(os.getenv("DISCORD_AUTHORIZED_USER_ID", 0))
AUTHORIZED_USER_ID2 = int(os.getenv("DISCORD_AUTHORIZED_USER_ID2", 0))

intents = Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Trade processing queue and lock
trade_queue = asyncio.Queue()
trade_lock = asyncio.Lock()


async def trade_worker():
    """Dedicated worker for processing trades sequentially"""
    while True:
        trade = await trade_queue.get()
        try:
            # Execute trade in a thread to avoid blocking event loop
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, handle_trade, trade)
            print(f"✅ Trade completed: {result}")
        except Exception as e:
            print(f"🔥 Trade execution failed: {str(e)}")
        finally:
            trade_queue.task_done()


@bot.event
async def on_ready():
    print(f"[✓] Logged in as {bot.user}")
    # Start the trade worker task
    asyncio.create_task(trade_worker())

    ch = bot.get_channel(BROADCAST_CHANNEL_ID)
    if ch:
        await ch.send("✅ Bot is online and ready to broadcast!")


@bot.event
async def on_message(message: Message):
    # Authorization check
    if message.author.id not in [AUTHORIZED_USER_ID, AUTHORIZED_USER_ID2]:
        return

    # Additional name filter
    if not ("bishop-ideas" in message.author.name or "aa" in message.author.name):
        return

    print(f"📩 Processing message from {message.author}")

    if not message.embeds:
        output=message.content

    else:
        # Process embeds
        output_parts = []

        for embed in message.embeds:
            if embed.title:
                output_parts.append(embed.title)
            if embed.description:
                output_parts.append(embed.description)

        output = " ".join(output_parts).strip()

    if output:
        trades = parse_message(output)
        if trades:
            for trade in trades:
                future = submit_trade(trade)  # Returns future for tracking

                # Optional: Check status after delay
                if future:
                    await asyncio.sleep(5)
                    if future.done():
                        try:
                            result = future.result()
                            await message.channel.send(f"✅ Order executed: {result}")
                        except Exception as e:
                            await message.channel.send(f"❌ Order failed: {e}")

    # Process attachments
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith('image'):
            try:
                image_data = await attachment.read()
                text = ocr_from_screenshot(image_data)
                trades = parse_message(text)
                if trades:
                    async with trade_lock:
                        for trade in trades:
                            await trade_queue.put(trade)
                            print(f"⏳ Queued trade from image: {trade}")
            except Exception as e:
                print(f"❌ Image processing failed: {str(e)}")


def start_bot():
    bot.run(DISCORD_TOKEN)