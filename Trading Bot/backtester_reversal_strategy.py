import os
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator
from tqdm import tqdm
import matplotlib.pyplot as plt
import time

# Configuration Parameters
TICKERS = ['SPXL']  # List of tickers to backtest
INTERVAL = '1m'  # Data interval for day trading ('1m', '5m', '15m', '30m', '60m', '1d')
PERIOD = "1d"
INITIAL_BALANCE = 500  # Initial balance for backtesting

# Indicators Parameters
FIBONACCI_SMA_PERIODS = [5, 8, 13]  # Fibonacci periods for SMAs
RSI_WINDOW = 10  # Window for RSI calculation
RSI_BUY_THRESHOLD = 30  # RSI threshold for buying
RSI_SELL_THRESHOLD = 70  # RSI threshold for selling
BB_WINDOW = 8  # Window for Bollinger Bands

class Backtester:
    def __init__(self, tickers, initial_balance, interval):
        self.tickers = tickers
        self.initial_balance = initial_balance
        self.data = {}
        self.interval = interval
        self.data_directory = 'data'
        
    def fetch_data(self):
        for symbol in tqdm(TICKERS, desc="• Grabbing technical metrics for tickers"):
            try:
                Ticker = yf.Ticker(symbol)
                data = Ticker.history(period=PERIOD, interval=INTERVAL)
                data = data.sort_index()
                if data.empty:
                    print(f"No data found for {symbol}")
                    continue

            except KeyError as e:
                print(f"KeyError for {symbol}: {e}")
                continue

            self.data[symbol] = data
    
    def compute_indicators(self):
        for symbol, data in self.data.items():
            if data.empty:
                continue
            
            # Compute Fibonacci SMAs
            sma_columns = []
            for n in FIBONACCI_SMA_PERIODS:
                column_name = f'SMA{n}'
                data[column_name] = data['Close'].rolling(window=n).mean()
                sma_columns.append(column_name)

            data['SMA_BB'] = data[sma_columns].mean(axis=1)
            
            # Compute RSI
            rsi = RSIIndicator(close=data["Close"], window=RSI_WINDOW).rsi()
            data['RSI'] = rsi
            
            # Compute Bollinger Bands
            data['Rolling Std Dev'] = data['Close'].rolling(window=BB_WINDOW).std()
            data['Upper Band'] = data['SMA_BB'] + (data['Rolling Std Dev'] * 1)
            data['Lower Band'] = data['SMA_BB'] - (data['Rolling Std Dev'] * 1)
            
            self.data[symbol] = data.dropna()

    def backtest(self):
        results = {}
        for symbol, data in self.data.items():
            if data.empty:
                print(f"No data available for {symbol}.")
                continue
            
            data['Position'] = 0
            data['Trade'] = 0  # +1 for buy
            balance = self.initial_balance

            data['Account Value'] = balance
            
            # Simulate trading
            for i in range(1, len(data)):
                if data['RSI'].iloc[i] < RSI_BUY_THRESHOLD and data['Close'].iloc[i] < data['Lower Band'].iloc[i]:  # Buy signal


                    data.at[data.index[i], 'Trade'] = 1
                elif data['RSI'].iloc[i] > RSI_SELL_THRESHOLD and data['Close'].iloc[i] > data['Upper Band'].iloc[i]:  # Sell signal


                    data.at[data.index[i], 'Trade'] = -1
                
            

            # Store results for plotting
            results[symbol] = data

        self.plot_results(results)

    def plot_results(self, results):
        for symbol, data in results.items():
            # Plot price, buy/sell signals, and Bollinger Bands
            plt.figure(figsize=(14, 10))
            
            # Price and Bands
            plt.subplot(2, 1, 1)
            plt.plot(data.index, data['Close'], label='Price', color='blue')
            plt.plot(data.index, data['Upper Band'], label='Upper Band', color='orange', linestyle='--')
            plt.plot(data.index, data['Lower Band'], label='Lower Band', color='orange', linestyle='--')
            plt.plot(data.index, data['SMA_BB'], label='SMA of Bands', color='green', linestyle='--')
            
            # Plot buy and sell signals
            buy_signals = data[data['Trade'] == 1]
            sell_signals = data[data['Trade'] == -1]
            plt.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='g', label='Buy Signal', s=100)
            plt.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='r', label='Sell Signal', s=100)
            
            plt.title(f'{symbol} Price with Buy and Sell Signals')
            plt.legend()
            plt.grid()
            
            # Plot RSI
            plt.subplot(2, 1, 2)
            plt.plot(data.index, data['RSI'], label='RSI', color='purple')
            plt.axhline(RSI_BUY_THRESHOLD, color='green', linestyle='--', label='Buy Threshold')
            plt.axhline(RSI_SELL_THRESHOLD, color='red', linestyle='--', label='Sell Threshold')
            plt.title(f'{symbol} RSI')
            plt.legend()
            plt.grid()

            plt.tight_layout()
            plt.show()

if __name__ == "__main__":
    backtester = Backtester(TICKERS, INITIAL_BALANCE, INTERVAL)
    backtester.fetch_data()
    backtester.compute_indicators()
    backtester.backtest()
