import os
import logging
from ib_insync import IB, Option, MarketOrder, LimitOrder, util
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Setup
load_dotenv()
util.patchAsyncio()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ibkr')

# IBKR connection info
HOST = os.getenv("HOSTID", "127.0.0.1")
PORT = int(os.getenv("ENVIRONMENT", 4002))
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

def place_order(contract, action, quantity, order_type="MKT", limit_price=None):
    if order_type == "MKT":
        order = MarketOrder(action, quantity)
    elif order_type == "LMT" and limit_price:
        order = LimitOrder(action, quantity, limit_price)
    else:
        raise ValueError("Invalid order type")
    order.outsideRth = True
    order.account = ib.managedAccounts()[0]
    trade = ib.placeOrder(contract, order)
    logger.info(f"✅ Order submitted: {action} {quantity} {contract.symbol}")
    return trade

def handle_trade(trade_data):
    try:
        connect_ib()
        contract = resolve_contract(
            trade_data['symbol'],
            trade_data['expiry'],
            trade_data['strike'],
            trade_data['contract_type']
        )
        trade = place_order(
            contract,
            trade_data['action'],
            trade_data['quantity'],
            trade_data.get('order_type', 'MKT'),
            trade_data.get('limit_price')
        )
        return trade
    except Exception as e:
        logger.error(f"Trade failed: {e}")
        return None

def submit_trade(trade_data):
    future = executor.submit(handle_trade, trade_data)
    return future
