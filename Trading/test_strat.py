class BuyHoldStrategy:
    def __init__(self, initial_ticker):
        self.initial_ticker = initial_ticker

    def get_buy_tickers(self):
        # Return a list with the single stock to buy
        return [self.initial_ticker]

    def get_sell_tickers(self, df=None):
        # For this simple strategy, no sell criteria are implemented
        return []

# Example usage in your Alpaca_framework.py
if __name__ == "__main__":
    strategy = BuyHoldStrategy("AAPL")  # Replace with your desired ticker
    tickers_to_buy = strategy.get_buy_tickers()
    print("Tickers to buy:", tickers_to_buy)
