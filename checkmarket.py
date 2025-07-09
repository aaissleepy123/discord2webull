# from ib_insync import IB, Option, util
# import time
# import math
#
# # Initialize
# util.patchAsyncio()
# ib = IB()
# ib.connect('127.0.0.1', 4001, clientId=86)  # use 4001 if on IB Gateway
#
# # Define QQQ 560 Put expiring 2025-06-25
# contract = Option('QQQ', '20250627', 560, 'P', exchange='SMART')
# ib.qualifyContracts(contract)
#
# # Request market data
# ticker = ib.reqMktData(contract, '', False, False)
#
# # Wait for bid/ask to populate
# start = time.time()
# while (
#     ticker.bid is None or ticker.ask is None or
#     math.isnan(ticker.bid) or math.isnan(ticker.ask)
# ) and time.time() - start < 5:
#     ib.sleep(0.2)
#
# # Print bid/ask or error
# if ticker.bid is not None and ticker.ask is not None:
#     print(f"✅ Bid: {ticker.bid}, Ask: {ticker.ask}")
# else:
#     print("❌ Failed to retrieve bid/ask (still None or NaN)")
#
# # Cleanup
# ib.cancelMktData(contract)
# ib.disconnect()

from ib_insync import IB, Option
import time

ib = IB()
ib.connect('127.0.0.1', 4001, clientId=86)

# STEP 1: Use reqContractDetails to get a valid option
details = ib.reqContractDetails(Option('QQQ', '', 549, 'C', exchange='SMART'))

# STEP 2: Pick one valid option (you can filter if needed)
contract = details[0].contract
print("Using contract:", contract)

# STEP 3: Qualify and request market data
ib.qualifyContracts(contract)
ticker = ib.reqMktData(contract, "", False, False)
ib.sleep(2)

# STEP 4: Print market data
print("Bid:", ticker.bid)
print("Ask:", ticker.ask)
print("Last:", ticker.last)

ib.disconnect()



