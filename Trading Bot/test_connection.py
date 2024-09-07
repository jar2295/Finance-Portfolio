from ib_insync import IB

def test_connection(host: str, port: int, client_id: int):
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        print("Connected successfully")
        ib.disconnect()
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_connection('localhost', 7497, 0)
