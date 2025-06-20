from ib_insync import IB, MarketOrder


def clearpositions():
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=3)

    positions = ib.positions()
    print(positions)

    # Print account summary
    summary = ib.accountSummary()
    for s in summary:
        print(f"{s.tag}: {s.value}")

    # Go through positions and close them
    for pos in positions:
        contract = pos.contract

        # Get full contract details
        details = ib.reqContractDetails(contract)
        if not details:
            print(f"⚠ Could not resolve contract details for {contract.localSymbol}")
            continue

        full_contract = details[0].contract
        position_size = pos.position

        if position_size != 0:
            action = 'SELL' if position_size > 0 else 'BUY'
            quantity = abs(position_size)

            print(f"Submitting {action} {quantity} {full_contract.localSymbol}")
            order = MarketOrder(action, quantity)
            order.outsideRth = True  # optional if you want to allow trading outside regular hours
            trade = ib.placeOrder(full_contract, order)

            # Wait until filled or cancelled
            while trade.orderStatus.status not in ('Filled', 'Cancelled'):
                ib.waitOnUpdate(timeout=1)

            print(f"✅ Order status: {trade.orderStatus.status}")

    # Final PnL summary
    portfolio = ib.portfolio()
    total_realized = sum(p.realizedPNL for p in portfolio)
    total_unrealized = sum(p.unrealizedPNL for p in portfolio)
    ib.disconnect()
    return f"🔥 Today's Realized PnL: {total_realized}", f"📊 Current Unrealized PnL: {total_unrealized}"

