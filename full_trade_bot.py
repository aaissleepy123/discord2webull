import os
import re
import time
import spacy
import pytz
import pyotp
import nltk
import pytesseract
import logging
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter
from datetime import datetime
from discord.ext import commands
from discord import Intents, Message
from webull import paper_webull
from dotenv import load_dotenv
from llm import LLM
llm=LLM()

# ========== Setup ========== #
logging.basicConfig(level=logging.INFO)
load_dotenv()
nltk.download('punkt')
nlp = spacy.load("en_core_web_sm")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
USERNAME = os.getenv("WEBULL_USERNAME")
PASSWORD = os.getenv("WEBULL_PASSWORD")
DEVICE_NAME = os.getenv("DEVICE_NAME", "trade-bot-client")
MFA_TYPE = os.getenv("MFA_TYPE", "sms")
TOTP_SECRET = os.getenv("TOTP_SECRET", "")
REGION = os.getenv("REGION", "us")
BROADCAST_CHANNEL_ID = int(os.getenv("DISCORD_BROADCAST_CHANNEL_ID", 0))

TRADE_REGEX = re.compile(
    r"Option:\s*(?P<symbol1>\w+)\s+(?P<strike1>\d+(?:\.\d+)?)\s+(?P<contract1>[CP])\s+(?P<expiry1>\d+/\d+).*?"
    r"Entry:\s*@?\$?(?P<entry1>\d+(?:\.\d+)?)",
    re.IGNORECASE | re.DOTALL
)



# ========== Webull ========== #
w = paper_webull()
recent_trade_times = {}
session_active = False

def login():
    global session_active
    if session_active:
        return
    w.login(username=USERNAME, password=PASSWORD, device_name=DEVICE_NAME)
    if MFA_TYPE == 'sms':
        code = input("[!] Enter SMS verification code: ")
        w.login_step_2(code)
    elif MFA_TYPE == 'authenticator':
        code = pyotp.TOTP(TOTP_SECRET).now()
        w.login_step_2(code)
    session_active = True

def place_option_order(symbol, action, quantity, strike_price, expiry_date, option_type, limit_price, time_in_force='GTC'):
    chain = w.get_options(symbol=symbol)
    key = 'call' if option_type.upper() == 'C' else 'put'
    contracts = chain.get(key, [])
    contract = next((c for c in contracts if float(c.get('strikePrice')) == strike_price and c.get('expirationDate') == expiry_date), None)
    if contract:
        contract_id = contract.get('tickerId')
        w.place_option_order(
            stock_ticker=symbol,
            action=action,
            order_type='LMT',
            enforce=time_in_force,
            quant=quantity,
            price=limit_price,
            outside_regular_trading_hour=True,
            option_id=contract_id
        )

# ========== Discord Bot Setup ========== #
intents = Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[✓] Logged in as {bot.user}")
    try:
        if BROADCAST_CHANNEL_ID:
            ch = bot.get_channel(BROADCAST_CHANNEL_ID)
            if ch:
                await ch.send("✅ Bot is online and ready to broadcast!")
            else:
                print("[x] Broadcast channel not found or bot not in that channel.")
    except Exception as e:
        print(f"[!] Startup message error: {e}")

@bot.event
async def on_message(message: Message):

    print(f"[msg] Received: {message.content}")

    # Regular text parsing
    trades = parse_message(message.content)
    print(f"[parse] From text: {trades}")
    for trade in trades:
        await handle_trade(trade)

    # OCR image parsing
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image"):
            image_bytes = await attachment.read()
            ocr_text = ocr_from_screenshot(image_bytes)
            print(f"[ocr] From image: {ocr_text}")
            trades = parse_message(ocr_text)
            print(f"[parse] From image: {trades}")
            for trade in trades:
                await handle_trade(trade)

    # ✅ NEW: Parse embed text
    for embed in message.embeds:
        if embed.description:
            print(f"[embed] Found description: {embed.description}")
            trades = parse_message(embed.description)
            print(f"[parse] From embed: {trades}")
            for trade in trades:
                await handle_trade(trade)

        if embed.fields:
            for field in embed.fields:
                print(f"[embed] Field: {field.name} = {field.value}")
                trades = parse_message(field.name + "\n" + field.value)
                print(f"[parse] From embed field: {trades}")
                for trade in trades:
                    await handle_trade(trade)

# ========== Helpers ========== #
def parse_message(text):
    trades = []
    match = TRADE_REGEX.search(text)

    if match:
        # Contract-style
        if match.group("symbol1"):
            trades.append({
                "symbol": match.group("symbol1").upper(),
                "expiry": match.group("expiry1"),
                "strike": float(match.group("strike1")),
                "entry": float(match.group("entry1")),
                "contract_type": match.group("contract1").upper(),
                "timestamp": datetime.utcnow().isoformat(),
                "source": text.strip()
            })

        # Option-style
        elif match.group("symbol2"):
            trades.append({
                "symbol": match.group("symbol2").upper(),
                "expiry": match.group("expiry2"),
                "strike": float(match.group("strike2")),
                "entry": float(match.group("entry1")),
                "contract_type": match.group("contract2").upper(),
                "timestamp": datetime.utcnow().isoformat(),
                "source": text.strip()
            })

        return trades

    # Fallback logic using NLP to extract basic structure
    for line in text.splitlines():
        tokens = [token.text for token in nlp(line)]
        potential_symbol = next((t for t in tokens if t.isalpha() and len(t) <= 5), None)
        potential_entry = next((t for t in tokens if re.fullmatch(r"\d+(\.\d+)?", t)), None)

        if potential_symbol and potential_entry:
            trades.append({
                "symbol": potential_symbol.upper(),
                "expiry": None,
                "strike": 0.0,
                "entry": float(potential_entry),
                "contract_type": "C",
                "timestamp": datetime.utcnow().isoformat(),
                "source": line.strip()
            })

    return trades


def ocr_from_screenshot(screenshot_bytes):
    image = Image.open(BytesIO(screenshot_bytes)).convert("L")
    image = image.filter(ImageFilter.SHARPEN)
    image = ImageEnhance.Contrast(image).enhance(2.0)
    text = pytesseract.image_to_string(image)
    return text

async def handle_trade(trade):
    now = time.time()
    key = f"{trade['symbol']}-{trade['expiry']}-{trade['strike']}-{trade['entry']}"
    last_time = recent_trade_times.get(key, 0)
    if now - last_time < 10:
        print("[skip] Duplicate trade")
        return
    recent_trade_times[key] = now

    if not BROADCAST_CHANNEL_ID:
        print("[x] Broadcast channel ID not set in .env.")
        return

    channel = bot.get_channel(BROADCAST_CHANNEL_ID)
    if not channel:
        print("[x] Could not access broadcast channel.")
        return

    try:
        await send_trade_alert(channel, trade)
        print("[+] Trade alert sent")
    except Exception as e:
        print(f"[x] Broadcast failed: {e}")
        return

    if not trade.get('expiry') or not trade.get('strike'):
        print("[~] Incomplete trade — alert sent, skipping order placement")
        return

    try:
        login()
    except Exception as e:
        print(f"[x] Webull login failed: {e}")
        return

    try:
        place_option_order(
            symbol=trade['symbol'],
            action='BUY',
            quantity=1,
            strike_price=trade['strike'],
            expiry_date=trade['expiry'],
            option_type=trade.get('contract_type', 'C'),
            limit_price=trade['entry']
        )
        print("[+] Order placed")
    except Exception as e:
        print(f"[x] Order failed: {e}")

async def send_trade_alert(channel, trade):
    msg = (
        f"**📣 Trade Alert**\n"
        f"**Symbol:** `{trade['symbol']}`\n"
        f"**Type:** `{trade['contract_type']}`\n"
        f"**Strike:** `{trade.get('strike', 'N/A')}`\n"
        f"**Expiry:** `{trade.get('expiry', 'N/A')}`\n"
        f"**Entry:** `${trade.get('entry', 'N/A')}`\n"
        f"**Qty:** `{trade.get('quantity', 1)}`\n"
        f"**Time:** `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC`"
    )
    await channel.send(msg)

# ========== Run ========== #
if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
