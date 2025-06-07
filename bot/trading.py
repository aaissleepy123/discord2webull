from ib_insync import IB, Option, MarketOrder


class MarketOrderExecutor:
    def __init__(self, trades=None):  # Make trades optional
        self.ib = IB()
        self.trades = trades

    def connect(self):
        """Connect to TWS/Gateway"""
        if not self.ib.isConnected():
            self.ib.connect('127.0.0.1', 7497, clientId=1)
            print("Connected to IBKR")

    def execute_from_parser(self, parsed_trade):
        """
        Execute market order using output from parse_message()

        Args:
            parsed_trade: Dict with keys:
                symbol (str)
                contract_type (str 'C'/'P')
                expiry (str 'YYYYMMDD')
                strike (float)
                action (str 'BUY'/'SELL')
                quantity (int)
        """
        self.connect()

        contract = Option(
            symbol=parsed_trade['symbol'],
            lastTradeDateOrContractMonth=parsed_trade['expiry'],
            strike=parsed_trade['strike'],
            right=parsed_trade['contract_type'],
            exchange='SMART'
        )

        self.ib.qualifyContracts(contract)

        order = MarketOrder(
            action=parsed_trade['action'],
            totalQuantity=parsed_trade['quantity']
        )

        trade = self.ib.placeOrder(contract, order)

        print(
            f"Executed: {parsed_trade['action']} {parsed_trade['quantity']} "
            f"{parsed_trade['symbol']} {parsed_trade['strike']}"
            f"{parsed_trade['contract_type']}\n"
            f"Source: {parsed_trade.get('source_text', 'N/A')}"
        )
        return trade

    def disconnect(self):
        """Close connection"""
        if self.ib.isConnected():
            self.ib.disconnect()
            print("Disconnected from IBKR")


def handle_trade(trade):
    """Function expected by core.py"""
    executor = MarketOrderExecutor()  # Don't pass trades here unless needed
    try:
        executor.connect()
        executor.execute_from_parser(trade)  # Note: changed from execute_trade to execute_from_parser
    finally:
        executor.disconnect()