from ib_insync import IB, MarketOrder

def clearpositions():
    ib = IB()
    ib.connect('127.0.0.1', 4001, clientId=3)

    positions = ib.positions()
    total_pnl = 0.0

    for pos in positions:
        contract = pos.contract
        details = ib.reqContractDetails(contract)
        if not details:
            print(f"⚠ Could not resolve contract details for {contract.localSymbol}")
            continue

        full_contract = details[0].contract
        position_size = pos.position
        avg_cost = pos.avgCost
        multiplier = float(full_contract.multiplier or 1)

        if position_size != 0:
            action = 'SELL' if position_size > 0 else 'BUY'
            quantity = abs(position_size)

            order = MarketOrder(action, quantity)
            order.outsideRth = True
            trade = ib.placeOrder(full_contract, order)

            while trade.orderStatus.status not in ('Filled', 'Cancelled'):
                ib.waitOnUpdate(timeout=1)

            if trade.orderStatus.status == 'Filled':
                fill_price = trade.orderStatus.avgFillPrice
                if position_size > 0:
                    pnl = (fill_price - avg_cost) * position_size * multiplier
                else:
                    pnl = (avg_cost - fill_price) * abs(position_size) * multiplier
                total_pnl += pnl
                print(f"✅ Closed {quantity} {full_contract.localSymbol} at {fill_price}, PnL: {pnl:.2f}")

    ib.disconnect()
    return f"🔥SLAYYYY QUEEN!! You cleared positions PnL: {total_pnl:.2f} USD"
