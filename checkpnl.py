from ib_insync import IB

def check_pnl():
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=5)

    summary = ib.accountSummary()

    realized = next((s.value for s in summary if s.tag == 'RealizedPnL'), 'N/A')
    unrealized = next((s.value for s in summary if s.tag == 'UnrealizedPnL'), 'N/A')
    ib.disconnect()
    return (f"🔥 Realized PnL: {realized} | 📊 Unrealized PnL: {unrealized}")

