import pandas as pd
import yfinance as yf
from tqdm import tqdm
import matplotlib.pyplot as plt
from strategy import Strategy  # Import your strategy module

class Backtester:
    def __init__(self, strategy: Strategy, tickers: list):
        self.strategy = strategy
        self.tickers = tickers
        self.results = {}
        
    def fetch_data(self):
        for symbol in tqdm(self.tickers, desc="Fetching historical data"):
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d", interval='1m')  # Adjust period and interval as needed
                data = data.sort_index()
                if data.empty:
                    print(f"No data found for {symbol}")
                    continue

                # Store the data in the results dictionary
                self.results[symbol] = data

            except KeyError as e:
                print(f"KeyError for {symbol}: {e}")
                continue

    def apply_strategy(self):
        # Load the data into the strategy
        self.strategy.data = {}
        for symbol, data in self.results.items():
            try:
                # Apply strategy calculations
                self.strategy.data[symbol] = data.copy()
                self.strategy.data[symbol] = self.strategy.calculate_indicators(self.strategy.data[symbol])
            except KeyError as e:
                print(f"KeyError processing {symbol}: {e}")
                continue

    def generate_signals(self):
        buy_signals = {}
        sell_signals = {}

        for symbol, data in self.strategy.data.items():
            # Use the strategy methods to get buy/sell signals
            buy_signals[symbol] = self.strategy.get_buy_tickers()
            sell_signals[symbol] = self.strategy.get_sell_tickers()

        return buy_signals, sell_signals

    def plot_results(self):
        for symbol, data in self.strategy.data.items():
            plt.figure(figsize=(14, 7))
            
            plt.plot(data.index, data['Close'], label='Close Price', color='black')
            
            if 'Upper Band' in data.columns and 'Lower Band' in data.columns:
                plt.plot(data.index, data['Upper Band'], label='Upper Band', color='red', linestyle='--')
                plt.plot(data.index, data['Lower Band'], label='Lower Band', color='red', linestyle='--')
                plt.plot(data.index, data['SMA_BB'], label='Middle Band', color='blue', linestyle='--')
            
            # Plot buy and sell signals
            buy_actions = self.strategy.get_buy_tickers()
            sell_actions = self.strategy.get_sell_tickers()
            
            # Plot buy signals
            if buy_actions:
                plt.scatter(
                    [action['date'] for action in buy_actions],
                    [action['price'] for action in buy_actions],
                    marker='^', 
                    color='green', 
                    label='Buy Signal', 
                    zorder=5
                )
            
            # Plot sell signals
            if sell_actions:
                plt.scatter(
                    [action['date'] for action in sell_actions],
                    [action['price'] for action in sell_actions],
                    marker='v', 
                    color='red', 
                    label='Sell Signal', 
                    zorder=5
                )
            
            plt.title(f'{symbol} - Bollinger Bands & SMAs')
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.legend()
            plt.grid()
            plt.show()

if __name__ == "__main__":
    strategy = Strategy()  # Initialize your strategy
    tickers = ["AAPL"]  # Example list of tickers
    backtester = Backtester(strategy, tickers)
    backtester.fetch_data()
    backtester.apply_strategy()
    buy_signals, sell_signals = backtester.generate_signals()
    print("Buy Signals:", buy_signals)
    print("Sell Signals:", sell_signals)
    backtester.plot_results()
