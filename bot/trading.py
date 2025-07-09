import os
import logging
from ib_insync import IB, Option, MarketOrder, LimitOrder, util
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import time
import math
# Setup
load_dotenv()
util.patchAsyncio()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ibkr')

# IBKR connection info
HOST = os.getenv("HOSTID", "127.0.0.1")
PORT = int(os.getenv("ENVIRONMENT", 4001))
CLIENT_ID = int(os.getenv("CLIENTID", 1))

# IBKR setup
ib = IB()
executor = ThreadPoolExecutor(max_workers=1)

def connect_ib():
    if not ib.isConnected():
        ib.connect(HOST, PORT, clientId=CLIENT_ID)
        logger.info("✅ Connected to IBKR")

def resolve_contract(symbol, expiry, strike, right):
    contract = Option(symbol, expiry, strike, right, exchange="SMART", currency="USD")
    ib.qualifyContracts(contract)
    if not contract.conId:
        raise ValueError("Contract qualification failed")
    return contract

def cancel_pending_orders():
    connect_ib()  # Ensure we're connected
    ib.reqAllOpenOrders()
    ib.sleep(1)

    open_trades = ib.openTrades()
    cancelled = []

    for trade in open_trades:
        order_id = trade.order.orderId
        status = trade.orderStatus.status
        filled = trade.orderStatus.filled

        if status in ('Submitted', 'PreSubmitted', 'PendingSubmit') and filled == 0:
            ib.cancelOrder(trade.order)
            logger.info(f"🔁 Sent cancel request for Order {order_id}")
            ib.sleep(0.5)

            # Confirm cancellation
            ib.reqAllOpenOrders()
            ib.sleep(0.5)
            remaining_orders = [o.orderId for o in ib.openOrders()]
            if order_id not in remaining_orders:
                logger.info(f"✅ Confirmed cancelled: Order {order_id}")
                cancelled.append(order_id)
            else:
                logger.warning(f"❗ Still active or partially filled: Order {order_id}")

    if not cancelled:
        logger.info("📭 No eligible pending orders to cancel")
    return cancelled


def place_order(contract, action, quantity):
    # Request live market data
    ticker = ib.reqMktData(contract, "", False, False)

    # Poll for market data up to 5 seconds
    start = time.time()
    while (
        ticker.bid is None or ticker.ask is None or
        math.isnan(ticker.bid) or math.isnan(ticker.ask)
    ) and time.time() - start < 10:
        ib.sleep(0.2)

    ask_price = ticker.ask
    bid_price = ticker.bid
    print("ask price:", ask_price)
    print("bid price:", bid_price)

    ib.cancelMktData(contract)

    accounts = ib.managedAccounts()
    if not accounts:
        raise ValueError("No managed accounts available")

    # Decide order type
    if (
        ask_price is None or bid_price is None or
        math.isnan(ask_price) or math.isnan(bid_price)
    ):
        logger.warning("⚠️ Falling back to MARKET order due to missing or invalid bid/ask")
        order = MarketOrder(action, quantity)
    else:
        if action == "SELL":
            price = ask_price
            order = LimitOrder(action, quantity, price)
            logger.info(f"✅ SELL at ask price {price}")
        elif action == "BUY":
            price = bid_price
            order = LimitOrder(action, quantity, price)
            logger.info(f"✅ BUY at bid price {price}")
        else:
            raise ValueError("Action must be BUY or SELL")

    order.account = accounts[0]
    order.outsideRth = True

    # Place the order
    trade = ib.placeOrder(contract, order)
    if trade is None:
        logger.error("❌ Order placement failed: ib.placeOrder returned None")

    logger.info(f"✅ Order submitted: {action} {quantity} {contract.symbol}")
    return trade

# def place_order(contract, action, quantity):
#     ib.qualifyContracts(contract)
#     if not contract.conId:
#         raise ValueError("❌ Contract qualification failed — conId missing")
#
#     print(f"Resolved contract: {contract}")
#
#     accounts = ib.managedAccounts()
#     if not accounts:
#         raise ValueError("❌ No managed accounts available")
#
#     order = MarketOrder(action, quantity)
#     order.account = accounts[0]
#     order.outsideRth = True
#
#     trade = ib.placeOrder(contract, order)
#     ib.sleep(1)
#
#     if trade is None:
#         logger.error("❌ Order placement failed: ib.placeOrder returned None")
#     elif trade.orderStatus.status.lower() in ['inactive', 'rejected']:
#         logger.error(f"❌ Order rejected with status: {trade.orderStatus.status}")
#
#     logger.info(f"✅ Market Order submitted: {action} {quantity} {contract.symbol}")
#     return trade
#

def handle_trade(trade_data):
    try:
        connect_ib()

        symbol = trade_data['symbol']
        expiry = trade_data['expiry']
        strike = trade_data['strike']
        right = trade_data['contract_type']
        action = trade_data['action']

        # 🚨 SAFETY CHECK: block naked SELLs
        if action.upper() == "SELL" and not has_contract_position(symbol, expiry, strike, right, ib):
            logger.warning(f"🛑 Blocked SELL — no position found for {symbol} {strike} {right} {expiry}")
            return None

        contract = resolve_contract(symbol, expiry, strike, right)
        trade = place_order(contract, action, trade_data['quantity'])

        return trade
    except Exception as e:
        logger.error(f"Trade failed: {e}")
        return None


def fetch_ibkr_positions_string(ib):
    positions = ib.positions()
    summaries = []

    for pos in positions:
        contract = pos.contract
        if hasattr(contract, 'symbol') and hasattr(contract, 'right') and hasattr(contract, 'lastTradeDateOrContractMonth'):
            if pos.position != 0:
                summaries.append(
                    f"{'LONG' if pos.position > 0 else 'SHORT'} {abs(pos.position)} "
                    f"{contract.symbol} {contract.right} {contract.strike} {contract.lastTradeDateOrContractMonth}"
                )

    if summaries:
        return " | ".join(summaries)
    else:
        return "No open positions"


def submit_trade(trade_data):
    future = executor.submit(handle_trade, trade_data)
    return future

def has_contract_position(symbol, expiry, strike, right, ib=ib):
    ib.qualifyContracts(Option(symbol, expiry, strike, right, exchange="SMART"))
    positions = ib.positions()
    for pos in positions:
        c = pos.contract
        if (
            c.symbol == symbol and
            c.lastTradeDateOrContractMonth == expiry and
            abs(c.strike - strike) < 0.01 and
            c.right.upper()[0] == right.upper()[0] and
            pos.position > 0
        ):
            return True
    return False
