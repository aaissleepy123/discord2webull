from ib_insync import IB, Option

def check_pnl():
    ib = IB()
    client_id = 10
    ib.connect('127.0.0.1', 4001, clientId=client_id)

    summary = {v.tag: v.value for v in ib.accountSummary()}
    positions = ib.portfolio()

    for pos in positions:
        contract = pos.contract
        ticker = ib.reqMktData(contract, "", False, False)
        ib.sleep(2)  # Let data flow in
        print(f"📝 {contract.localSymbol} | Bid: {ticker.bid}, Ask: {ticker.ask}, Last: {ticker.last}, Close: {ticker.close}")

    total_unrealized_pnl = sum(pos.unrealizedPNL for pos in positions)
    total_realized_pnl = sum(pos.realizedPNL for pos in positions)

    ib.disconnect()

    result = (
        f"📊 Unrealized PnL: {total_unrealized_pnl:.2f} USD\n"
        f"💵 Realized PnL: {total_realized_pnl:.2f} USD"
    )
    return result
