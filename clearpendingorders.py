from ib_insync import IB


def cancel_pending_orders():
    ib = IB()
    ib.connect('127.0.0.1', 4001, clientId=9)  # Use your clientId

    # Get all open orders
    all_orders = ib.reqAllOpenOrders()
    total_orders = len(all_orders)
    cancelled = []
    failed = []

    print(f"Found {total_orders} open orders:")

    # Try to cancel each order
    for trade in all_orders:
        order = trade.order
        contract = trade.contract
        try:
            ib.cancelOrder(order)
            cancelled.append(order.orderId)
            print(
                f"✓ Cancelled Order {order.orderId} - {contract.symbol} {order.action} {order.totalQuantity} @ {order.lmtPrice or 'MKT'}")
        except Exception as e:
            failed.append(order.orderId)
            print(f"✗ Failed to cancel Order {order.orderId}: {str(e)}")

    # Verification
    if not all_orders:
        print("No open orders found")
    elif len(cancelled) == total_orders:
        print("\n✅ SUCCESS: All orders cancelled successfully")
    else:
        print(f"\n⚠️ WARNING: Only {len(cancelled)}/{total_orders} orders cancelled")
        print("Failed to cancel these orders:")
        for order_id in failed:
            print(f" - Order {order_id}")

    ib.disconnect()
    return cancelled, failed
