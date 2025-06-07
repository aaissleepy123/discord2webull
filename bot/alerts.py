# from datetime import datetime
#
# async def send_trade_alert(channel, trade):
#     msg = (
#         f"**📣 Trade Alert**\n"
#         f"**Symbol:** `{trade['symbol']}`\n"
#         f"**Type:** `{trade['contract_type']}`\n"
#         f"**Strike:** `{trade.get('strike', 'N/A')}`\n"
#         f"**Expiry:** `{trade.get('expiry', 'N/A')}`\n"
#         f"**Entry:** `${trade.get('entry', 'N/A')}`\n"
#         f"**Qty:** `{trade.get('quantity', 1)}`\n"
#         f"**Time:** `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC`"
#     )
#     await channel.send(msg)
