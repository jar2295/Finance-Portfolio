from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time

class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.last_price = None
        self.data_received = threading.Event()
        self.done = threading.Event()

    def error(self, reqId: int, errorCode: int, errorString: str):
        print(f"Error: {reqId}, {errorCode}, {errorString}")

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        if tickType == 4:  # Last price
            self.last_price = price
            print(f"Last Price: {price}")
            self.data_received.set()  # Notify that data has been received

    def nextValidId(self, orderId: int):
        print(f"Next Valid Order ID: {orderId}")
        self.done.set()

    def tickSnapshotEnd(self, reqId: int):
        print("Snapshot data received.")
        self.data_received.set()

def run_loop():
    app.run()

# Create IBapi instance
app = IBapi()

# Start the socket in a thread
api_thread = threading.Thread(target=run_loop)
api_thread.start()

# Connect to IB
print("Connecting to IB...")
app.connect('127.0.0.1', 7497, 0)

# Wait for connection
app.done.wait(timeout=5)
print("Connected to IB")

# Create contract object
apple_contract = Contract()
apple_contract.symbol = 'AAPL'
apple_contract.secType = 'STK'
apple_contract.exchange = 'SMART'
apple_contract.currency = 'USD'

# Request snapshot data (note the last parameter is True for snapshot)
print("Requesting snapshot data...")
app.reqMktData(1, apple_contract, '', True, False, [])

# Wait for data to be received
print("Waiting for data...")
app.data_received.wait(timeout=15)  # Wait up to 15 seconds

if app.last_price is None:
    print("No data received within the timeout period.")
else:
    print(f"Received Last Price: {app.last_price}")

# Disconnect
app.disconnect()
api_thread.join()
print("Disconnected from IB")
