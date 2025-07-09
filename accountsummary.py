from ib_insync import IB

def account_summary():
    ib = IB()
    ib.connect('127.0.0.1', 4001, clientId=10)

    summaries = ib.accountSummary()
    # Extract balances for CAD and USD
    cash_cad = next((float(s.value) for s in summaries
                     if s.tag == 'CashBalance' and s.currency == 'CAD'), 0.0)
    cash_usd = next((float(s.value) for s in summaries
                     if s.tag == 'CashBalance' and s.currency == 'USD'), 0.0)

    ib.disconnect()

    return (
        f"💵 CAD Cash: {cash_cad:.2f} CAD\n"
        f"💵 USD Cash: {cash_usd:.2f} USD"
    )
