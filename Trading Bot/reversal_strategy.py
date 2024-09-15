import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator
from tqdm import tqdm
import numpy as np
import matplotlib.pyplot as plt
from new_alpaca_framework import Alpaca_trader
import time

class Strategy: 
    def __init__(self) -> None:
        self.fibonacci = [5, 8, 13]
        self.std_dev_multiplier = 1
        self.bb_window = 10
        self.rsi_window = 14
        self.rsi_upper = 70
        self.rsi_lower = 30
        self.data = {}
        self.alpaca_trader = Alpaca_trader()
        self.ticker = ['TSLA']  # Example tickers
        self.running = True  # Control flag for the loop

    def get_ticker_info(self):
        for symbol in tqdm(self.ticker, desc="• Grabbing technical metrics for tickers"):
            try:
                Ticker = yf.Ticker(symbol)
                data = Ticker.history(period="1d", interval='1m')
                data = data.sort_index()
                if data.empty:
                    print(f"No data found for {symbol}")
                    continue

                # Compute Fibonacci SMAs
                sma_columns = []
                for n in self.fibonacci:
                    column_name = f'SMA{n}'
                    data[column_name] = data['Close'].rolling(window=n).mean()
                    sma_columns.append(column_name)

                # Compute average of Fibonacci SMAs
                data['SMA_BB'] = data[sma_columns].mean(axis=1)

                # Compute RSI
                rsi = RSIIndicator(close=data["Close"], window=self.rsi_window).rsi()
                data['RSI'] = rsi

                # Compute Bollinger Bands
                data['Rolling Std Dev'] = data['Close'].rolling(window=self.bb_window).std()
                data['Upper Band'] = data['SMA_BB'] + (data['Rolling Std Dev'] * self.std_dev_multiplier)
                data['Lower Band'] = data['SMA_BB'] - (data['Rolling Std Dev'] * self.std_dev_multiplier)

                self.data[symbol] = data.dropna()

            except KeyError as e:
                print(f"KeyError for {symbol}: {e}")
                continue


    def calculate_indicators(self):
        self.get_ticker_info()

        for symbol, data in self.data.items():
            try:
                if (data['RSI'].iloc[-1] > self.rsi_upper) and (data["Close"].iloc[-1] < data['Upper Band'].iloc[-1]):
                    self.alpaca_trader.submit_sell_order(symbol, qty=1)  # Use instance method

                elif (data['RSI'].iloc[-1] < self.rsi_lower) and (data["Close"].iloc[-1] < data['Lower Band'].iloc[-1]):
                    self.alpaca_trader.submit_buy_order(symbol, qty=1)  # Use instance method

                else:
                    print(f"No action for {symbol}")

            except Exception as e:
                print(f"Error calculating indicators for {symbol}: {e}")
                continue

    def run(self):
        self.alpaca_trader.get_portfolio()

        while self.running:
            self.calculate_indicators()
            time.sleep(10)  # Wait for 1 minute before fetching new data

    def stop(self):
        self.running = False
        print("Stopping strategy...")

if __name__ == "__main__":
    strategy = Strategy()  # Initialize the strategy
    strategy.run()  # Start continuous data fetching and trading