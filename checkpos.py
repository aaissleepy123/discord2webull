from ib_insync import IB

def check_positions():
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=4)

    positions = ib.portfolio()  # includes marketPrice, marketValue, PnL info

    if not positions:
        print("✅ No open positions.")
    else:
        for pos in positions:
            contract = pos.contract
            print(f"📌 {contract.localSymbol} | {contract.secType} | "
                  f"Position: {pos.position} | Avg Cost: {pos.averageCost:.2f} | "
                  f"Market Price: {pos.marketPrice:.2f} | Market Value: {pos.marketValue:.2f}")

    ib.disconnect()

check_positions()
