from ib_insync import IB

def check_positions():
    ib = IB()
    ib.connect('127.0.0.1', 4001, clientId=4)

    positions = ib.portfolio()  # includes marketPrice, marketValue, PnL info
    ib.disconnect()
    if not positions:
        return "✅ No open positions."
    else:
        lines = []
        for pos in positions:
            contract = pos.contract
            lines.append(
                f"📌 {contract.localSymbol} | {contract.secType} | "
                f"Position: {pos.position} | Avg Cost: {pos.averageCost:.10f} | "
                f"Market Price: {pos.marketPrice:.10f} | Market Value: {pos.marketValue:.2f}"
            )
        return "\n".join(lines)


check_positions()
