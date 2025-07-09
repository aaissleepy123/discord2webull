from ib_insync import IB, Forex, MarketOrder


def convertcurrency():
    ib = IB()
    ib.connect('127.0.0.1', 4001, clientId=123)
    # USDCAD is the proper symbol
    fx_contract = Forex('USDCAD')

    # Qualify contract
    ib.qualifyContracts(fx_contract)

    # Amount of USD you want to BUY (or CAD you want to SELL)
    amount = 450  # Example: buy 220 USD worth (adjust as needed)

    # Create market order
    order = MarketOrder('BUY', amount)  # Buy USD, sell CAD

    # Attach account
    order.account = ib.managedAccounts()[0]

    # Place order
    trade = ib.placeOrder(fx_contract, order)

    # Let IB process
    ib.sleep(3)
    print(f"Order Status: {trade.orderStatus.status}")

    # Disconnect
    ib.disconnect()