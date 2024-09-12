import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator
from tqdm import tqdm
import numpy as np
import matplotlib.pyplot as plt

# Configuration Parameters
TICKERS = ['SPY']  # List of tickers to backtest
START_DATE = '2024-01-01'  # Start date for historical data
END_DATE = '2024-09-01'  # End date for historical data
INTERVAL = '1m'  # Data interval for day trading ('1m', '5m', '15m', '30m', '60m', '1d')
INITIAL_BALANCE = 1000  # Initial balance for backtesting

# Indicators Parameters
FIBONACCI_SMA_PERIODS = [5, 8, 13]  # Fibonacci periods for SMAs
RSI_WINDOW = 8  # Window for RSI calculation
RSI_BUY_THRESHOLD = 30  # RSI threshold for buying
RSI_SELL_THRESHOLD = 70  # RSI threshold for selling
BB_WINDOW = 8  # Window for Bollinger Bands

class Backtester:
    def __init__(self, tickers, start_date, end_date, initial_balance, interval):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        self.data = {}
        self.interval = interval
        
    def fetch_data(self):
        for symbol in tqdm(self.tickers, desc="Fetching historical data"):
            Ticker = yf.Ticker(symbol)
            data = Ticker.history(start=self.start_date, end=self.end_date, interval='1d')  # Use daily interval
            if data.empty:
                print(f"No data available for {symbol} during the specified period.")
            else:
                data = data.sort_index()
                print(f"Data for {symbol}:")
                print(data.head())  # Print first few rows to check data
                self.data[symbol] = data


    def compute_indicators(self):
        for symbol, data in self.data.items():
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
            data['Trade'] = 0  # +1 for buy, -1 for sell
            balance = self.initial_balance
            holdings = 0
            data['Account Value'] = balance
            
            # Simulate trading
            for i in range(1, len(data)):
                if data['RSI'].iloc[i] < RSI_BUY_THRESHOLD and balance > 0:  # Buy signal
                    holdings = balance / data['Close'].iloc[i]
                    balance = 0
                    data.at[data.index[i], 'Trade'] = 1
                elif data['RSI'].iloc[i] > RSI_SELL_THRESHOLD and holdings > 0:  # Sell signal
                    balance = holdings * data['Close'].iloc[i]
                    holdings = 0
                    data.at[data.index[i], 'Trade'] = -1
                
                # Update account value
                data.at[data.index[i], 'Account Value'] = balance + (holdings * data['Close'].iloc[i])
            
            # Final profit
            if not data.empty:
                final_value = balance + (holdings * data['Close'].iloc[-1])
                profit = final_value - self.initial_balance
                
                # Print results
                print(f"{symbol} Final Account Value: ${final_value:.2f}")
                print(f"{symbol} Total Profit: ${profit:.2f}")
            else:
                print(f"Error: Data is empty for {symbol}.")

            # Store results for plotting
            results[symbol] = data

        self.plot_results(results)

    def plot_results(self, results):
        for symbol, data in results.items():
            plt.figure(figsize=(12, 6))
            plt.plot(data.index, data['Close'], label='Price', color='blue')
            
            # Plot buy and sell signals
            buy_signals = data[data['Trade'] == 1]
            sell_signals = data[data['Trade'] == -1]
            
            plt.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='g', label='Buy Signal', s=100)
            plt.scatter(sell_signals.index, sell_signals['Close'], marker='v', color='r', label='Sell Signal', s=100)
            
            plt.title(f'{symbol} Price with Buy and Sell Signals')
            plt.legend()
            plt.show()

if __name__ == "__main__":
    backtester = Backtester(TICKERS, START_DATE, END_DATE, INITIAL_BALANCE, INTERVAL)
    backtester.fetch_data()
    backtester.compute_indicators()
    backtester.backtest()
