from ib_insync import IB
from datetime import datetime

def get_realized_pnl_today():
    ib = IB()
    ib.connect('127.0.0.1', 4001, clientId=79)

    now = datetime.now()
    today = now.date()
    executions = ib.reqExecutions()

    total_realized = 0.0

    for exec_detail in executions:
        exec_date = exec_detail.execution.time.date()  # no astimezone()
        if exec_date == today:
            report = exec_detail.commissionReport
            if report and report.realizedPNL is not None:
                total_realized += report.realizedPNL

    ib.disconnect()
    return f"✅ Realized PnL today: {total_realized:.2f}"
