import os
import time
import logging
import discord
from datetime import datetime
from discord.ext import commands
from discord import Intents, Message, Interaction
from discord.ui import View, button, Button
import asyncio
from dotenv import load_dotenv
from bot.ocr import ocr_from_screenshot
from bot.parser import parse_message
from bot.trading import submit_trade, handle_trade
from queuelookup import queuelookup
from clearpositions import clearpositions
from checkpnl import check_pnl
from checkpos import check_positions
from clearpendingorders import cancel_pending_orders
from convertmoney import convertcurrency
from getexecutions import list_contract_fills
from accountsummary import account_summary
from pnlday import get_realized_pnl_today

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

trade_queue = asyncio.Queue()
trade_lock = asyncio.Lock()

class ActionView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _send_blocking(self, interaction, func):
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(loop.run_in_executor(None, func), timeout=8)
            await interaction.response.send_message(result, ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.response.send_message("⏳ Request timed out.", ephemeral=True)

    @button(label="✅ Clear Position")
    async def clear(self, interaction: Interaction, button: Button):
        await self._send_blocking(interaction, clearpositions)

    @button(label="📊 Check Positions")
    async def check(self, interaction: Interaction, button: Button):
        await self._send_blocking(interaction, check_positions)

    @button(label="📈 PnL")
    async def pnl(self, interaction: Interaction, button: Button):
        await self._send_blocking(interaction, check_pnl)

    @button(label="❌ Cancel Pending")
    async def cancel(self, interaction: Interaction, button: Button):
        await self._send_blocking(interaction, cancel_pending_orders)

    @button(label="💵 Convert USD/CAD")
    async def convert(self, interaction: Interaction, button: Button):
        await self._send_blocking(interaction, convertcurrency)

    @button(label="📉 Get Executions")
    async def executions(self, interaction: Interaction, button: Button):
        await self._send_blocking(interaction, list_contract_fills)

    @button(label="📋 Account Summary")
    async def summary(self, interaction: Interaction, button: Button):
        await self._send_blocking(interaction, account_summary)

    @button(label="❓ Help")
    async def help(self, interaction: Interaction, button: Button):
        guide = (
            "**Bot Command Guide**\n"
            "• `check pos` → Shows open positions\n"
            "• `pnl` → Shows current PnL\n"
            "• `clear pos` → Closes all positions\n"
            "• `cancel pending` → Cancels all unfilled orders\n"
            "• `summary` → Shows account value, buying power\n"
            "• `how much did i make` → Today's realized PnL\n"
            "• `menu` → Brings up this interactive menu"
        )
        await interaction.response.send_message(guide, ephemeral=True)

@bot.command()
async def menu(ctx):
    await ctx.send("Choose an action:", view=ActionView())

async def trade_worker():
    while True:
        trade = await trade_queue.get()
        try:
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
    asyncio.create_task(trade_worker())
    asyncio.create_task(monitor_positions())
    ch = bot.get_channel(BROADCAST_CHANNEL_ID)
    if ch:
        await ch.send("✅ iiiii aaaammmmmmmmm reeeaaaadyyyyyy!")

@bot.event
async def on_message(message: Message):
    await bot.process_commands(message)

    if message.author.id not in [AUTHORIZED_USER_ID, AUTHORIZED_USER_ID2]:
        return

    name = message.author.name
    if "super cute" in name or not ("aa" in name or "bear-ideas" in name):
        #or "bishop" in name
        return


    output = message.content if not message.embeds else " ".join([
        (embed.title or "") + (embed.description or "") for embed in message.embeds
    ]).strip()
    print(f"📩 Processing message from {message.author}：{output}")
    if "setting trims" in output:
        return

    if output:
        lowered = output.lower()
        command_map = {
            "menu": lambda: message.channel.send("Choose an action:", view=ActionView()),
            "clear pos": lambda: message.channel.send(clearpositions()),
            "pnl": lambda: message.channel.send(check_pnl()),
            "check pos": lambda: message.channel.send(check_positions()),
            "summary": lambda: message.channel.send(account_summary()),
            "queue": lambda: message.channel.send(queuelookup()),
            "tyyy": lambda: message.channel.send("ur welcome! good luck bae <3"),
            "cancel pending": lambda: message.channel.send(cancel_pending_orders()),
            "how much did i make": lambda: message.channel.send(get_realized_pnl_today())
        }
        for key, action in command_map.items():
            if key in lowered:
                await action()
                return

        # Parse trade from message content
        trades = parse_message(output)
        if trades:
            async with trade_lock:
                for trade in trades:
                    try:
                        result = await asyncio.get_running_loop().run_in_executor(None, handle_trade, trade)
                        msg = f"✅ {result.order.action} {result.order.totalQuantity} {result.contract.localSymbol}"
                        await message.channel.send(msg)
                        await asyncio.sleep(1)
                        await message.channel.send(await asyncio.get_running_loop().run_in_executor(None, check_positions))
                    except Exception as e:
                        await message.channel.send(f"❌ Order failed: {e}")

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
                            await message.channel.send(f"⏳ Queued trade from image: {trade}")
            except Exception as e:
                await message.channel.send(f"❌ Failed to process image: {e}")


async def monitor_positions():
    while True:
        try:
            # Get current positions as formatted string
            positions_str = await asyncio.get_running_loop().run_in_executor(None, check_positions)

            if "No open positions" in positions_str:
                channel = bot.get_channel(BROADCAST_CHANNEL_ID)
                if channel:
                    await channel.send("noooooo positions")
                await asyncio.sleep(300)
                continue

            clearance_triggered = False
            messages = []

            # Parse each position line
            for line in positions_str.split('\n'):
                if not line.startswith('📌'):
                    continue

                # Extract position data
                parts = [p.strip() for p in line.split('|')]
                symbol = parts[0].split('📌')[1].split()[0].strip()

                try:
                    # Extract average cost and market price
                    avg_cost = float(parts[3].split(':')[1].strip())
                    market_price = float(parts[4].split(':')[1].strip())
                    market_price*=100

                    # Calculate profit percentage (SIMPLIFIED)
                    profit_pct = (market_price - avg_cost) / avg_cost * 100

                    # Check thresholds
                    if profit_pct <= -30:
                        messages.append(
                            f"🚨 **{symbol}** hit LOSS threshold: {profit_pct:.1f}% "
                            f"(Cost: {avg_cost:.2f} | Current: {market_price:.2f})"
                        )
                        clearance_triggered = True

                    elif profit_pct >= 50:
                        messages.append(
                            f"🎯 **{symbol}** hit GAIN threshold: {profit_pct:.1f}% "
                            f"(Cost: {avg_cost:.2f} | Current: {market_price:.2f})"
                        )
                        clearance_triggered = True

                except (ValueError, IndexError):
                    continue  # Skip if parsing fails

            # Take action if thresholds hit
            if clearance_triggered:
                channel = bot.get_channel(BROADCAST_CHANNEL_ID)
                if channel:
                    for msg in messages:
                        await channel.send(msg)
            else:
                channel = bot.get_channel(BROADCAST_CHANNEL_ID)
                if channel:
                    await channel.send("nah ur fine")

        except Exception as e:
            print(f"⚠️ Monitoring error: {e}")
        finally:
            await asyncio.sleep(300)  # Check every 10 seconds


def start_bot():
    bot.run(DISCORD_TOKEN)