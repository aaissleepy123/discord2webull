from ib_insync import IB

def queuelookup():
    ib = IB()
    ib.connect("127.0.0.1", 4001, clientId=10)

    ib.reqOpenOrders()  # Request all current open orders
    ib.sleep(1)  # Give IBKR a second to respond

    open_orders = ib.openOrders()

    if not open_orders:
        ib.disconnect()
        return "✅ No open orders at IBKR."

    lines = []
    for o in open_orders:
        lines.append(
            f"📌 OrderId: {o.orderId} | {o.action} {o.totalQuantity} {o.orderType} | Status: {o.orderStatus.status}"
        )

    ib.disconnect()
    return "\n".join(lines)
