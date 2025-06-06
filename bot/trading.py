import os
import time
import pyotp
from webull import paper_webull
from datetime import datetime

from .alerts import send_trade_alert

USERNAME = os.getenv("WEBULL_USERNAME")
PASSWORD = os.getenv("WEBULL_PASSWORD")
DEVICE_NAME = os.getenv("DEVICE_NAME", "trade-bot-client")
MFA_TYPE = os.getenv("MFA_TYPE", "sms")
TOTP_SECRET = os.getenv("TOTP_SECRET", "")
BROADCAST_CHANNEL_ID = int(os.getenv("DISCORD_BROADCAST_CHANNEL_ID", 0))

w = paper_webull()
session_active = False
recent_trade_times = {}

def login():
    global session_active
    if session_active:
        return
    w.login(username=USERNAME, password=PASSWORD, device_name=DEVICE_NAME)
    if MFA_TYPE == 'sms':
        w.login_step_2(input("[!] Enter SMS verification code: "))
    elif MFA_TYPE == 'authenticator':
        w.login_step_2(pyotp.TOTP(TOTP_SECRET).now())
    session_active = True

def place_option_order(symbol, action, quantity, strike_price, expiry_date, option_type, limit_price, time_in_force='GTC'):
    chain = w.get_options(symbol=symbol)
    key = 'call' if option_type.upper() == 'C' else 'put'
    contracts = chain.get(key, [])
    contract = next((c for c in contracts if float(c.get('strikePrice')) == strike_price and c.get('expirationDate') == expiry_date), None)
    if contract:
        w.place_option_order(
            stock_ticker=symbol,
            action=action,
            order_type='LMT',
            enforce=time_in_force,
            quant=quantity,
            price=limit_price,
            outside_regular_trading_hour=True,
            option_id=contract.get('tickerId')
        )

async def handle_trade(bot, trade):
    key = f\"{trade['symbol']}-{trade['expiry']}-{trade['strike']}-{trade['entry']}"
    if time.time() - recent_trade_times.get(key, 0) < 10:
        print(\"[skip] Duplicate trade")
        return
    recent_trade_times[key] = time.time()

    channel = bot.get_channel(BROADCAST_CHANNEL_ID)
    if not channel:
        print(\"[x] Could not access broadcast channel.")
        return

    try:
        await send_trade_alert(channel, trade)
        print(\"[+] Trade alert sent\")
    except Exception as e:
        print(f\"[x] Broadcast failed: {e}\")
        return

    if not trade.get('expiry') or not trade.get('strike'):
        print(\"[~] Incomplete trade — alert sent, skipping order placement\")
        return

    try:
        login()
        place_option_order(
            symbol=trade['symbol'],
            action=trade.get('action', 'BUY'),
            quantity=trade.get('quantity', 1),
            strike_price=trade['strike'],
            expiry_date=trade['expiry'],
            option_type=trade.get('contract_type', 'C'),
            limit_price=trade['entry']
        )
        print(\"[+] Order placed\")
    except Exception as e:
        print(f\"[x] Order failed: {e}\")
