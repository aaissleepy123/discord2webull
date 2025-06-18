from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=2)
print("Connected?", ib.isConnected())
ib.disconnect()
