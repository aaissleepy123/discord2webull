from ib_insync import IB

def list_contract_fills():
    ib = IB()
    ib.connect('127.0.0.1', 4001, clientId=48)

    execution_details = ib.reqExecutions()
    messages = []

    for detail in execution_details:
        contract = detail.contract
        report = detail.execution
        messages.append(
            f"✅ {report.time} | {contract.localSymbol} | "
            f"{report.side} {report.shares} @ ${report.price:.2f}"
        )

    ib.disconnect()

    if messages:
        return "\n".join(messages)
    else:
        return "No executions found."
