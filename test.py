import os
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from tqdm import tqdm
from itertools import product
import matplotlib.pyplot as plt
import time

# Configuration Parameters
TICKERS = ['SPXL']  # List of tickers to backtest
INTERVAL = '1m'  # Data interval for day trading ('1m', '5m', '15m', '30m', '60m', '1d')
PERIOD = "5d"
INITIAL_BALANCE = 500  # Initial balance for backtesting

# Define ranges for parameter optimization
FIBONACCI_SMA_PERIODS_GRID = [[5, 8, 13], [8, 13, 21], [13, 21, 34]]  # Different Fibonacci periods
RSI_WINDOW_GRID = [7, 10, 14]  # Different windows for RSI calculation
RSI_BUY_THRESHOLD_GRID = [25, 30, 35]  # RSI thresholds for buying
RSI_SELL_THRESHOLD_GRID = [65, 70, 75]  # RSI thresholds for selling
BB_WINDOW_GRID = [8, 10, 12]  # Bollinger Bands window
BB_MULTIPLIER = [1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2]

class Backtester:
    def __init__(self, tickers, initial_balance, interval, sma_periods, rsi_window, rsi_buy, rsi_sell, bb_window):
        self.tickers = tickers
        self.initial_balance = initial_balance
        self.data = {}
        self.interval = interval
        self.sma_periods = sma_periods
        self.rsi_window = rsi_window
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell
        self.bb_window = bb_window

    def fetch_data(self):
        for symbol in tqdm(self.tickers, desc="• Grabbing technical metrics for tickers"):
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
            for n in self.sma_periods:
                column_name = f'SMA{n}'
                data[column_name] = data['Close'].rolling(window=n).mean()
                sma_columns.append(column_name)

            data['SMA_BB'] = data[sma_columns].mean(axis=1)

            # Compute RSI
            rsi = RSIIndicator(close=data["Close"], window=self.rsi_window).rsi()
            data['RSI'] = rsi

            # Compute Rolling Standard Deviation for Bollinger Bands
            data['Rolling Std Dev'] = data['Close'].rolling(window=self.bb_window).std()

            # Compute Bollinger Bands for each multiplier
            for multiplier in BB_MULTIPLIER:
                data[f'Upper Band_{multiplier}'] = data['SMA_BB'] + (data['Rolling Std Dev'] * multiplier)
                data[f'Lower Band_{multiplier}'] = data['SMA_BB'] - (data['Rolling Std Dev'] * multiplier)

            self.data[symbol] = data.dropna()   


    def backtest(self):
        final_account_value = self.initial_balance
        for symbol, data in self.data.items():
            if data.empty:
                print(f"No data available for {symbol}.")
                continue

            balance = self.initial_balance
            shares = 0
            data['Position'] = 0  # Number of shares held
            data['Trade'] = 0  # +1 for buy, -1 for sell
            data['Account Value'] = balance

            # Simulate trading
            for i in range(1, len(data)):
                price = data['Close'].iloc[i]
                account_value = balance + shares * price

                # Buy condition
                if data['RSI'].iloc[i] < self.rsi_buy and data['Close'].iloc[i] < data['Lower Band'].iloc[i]:
                    if balance >= price:  # Ensure we have enough cash to buy
                        shares_to_buy = balance // price  # Number of shares to buy
                        balance -= shares_to_buy * price
                        shares += shares_to_buy
                        data.at[data.index[i], 'Trade'] = 1  # Buy signal

                # Sell condition
                elif data['RSI'].iloc[i] > self.rsi_sell and data['Close'].iloc[i] > data['Upper Band'].iloc[i]:
                    if shares > 0:  # Ensure we have shares to sell
                        balance += shares * price
                        shares = 0
                        data.at[data.index[i], 'Trade'] = -1  # Sell signal

                data.at[data.index[i], 'Account Value'] = account_value

            # Final account value after all trades
            final_account_value = balance + shares * data['Close'].iloc[-1]

        return final_account_value

# Parameter optimization using Grid Search
best_profit = float('-inf')
best_params = {}

# Iterate over all possible combinations of parameter values
for sma_periods, rsi_window, rsi_buy, rsi_sell, bb_window in product(
        FIBONACCI_SMA_PERIODS_GRID, RSI_WINDOW_GRID, RSI_BUY_THRESHOLD_GRID,
        RSI_SELL_THRESHOLD_GRID, BB_WINDOW_GRID):
    
    print(f"Testing with SMA periods: {sma_periods}, RSI window: {rsi_window}, "
          f"RSI buy threshold: {rsi_buy}, RSI sell threshold: {rsi_sell}, BB window: {bb_window}")
    
    # Initialize backtester with the current parameter set
    backtester = Backtester(TICKERS, INITIAL_BALANCE, INTERVAL, sma_periods, rsi_window, rsi_buy, rsi_sell, bb_window)
    backtester.fetch_data()
    backtester.compute_indicators()
    final_account_value = backtester.backtest()

    # Check if the current combination is the best so far
    if final_account_value > best_profit:
        best_profit = final_account_value
        best_params = {
            'FIBONACCI_SMA_PERIODS': sma_periods,
            'RSI_WINDOW': rsi_window,
            'RSI_BUY_THRESHOLD': rsi_buy,
            'RSI_SELL_THRESHOLD': rsi_sell,
            'BB_WINDOW': bb_window
        }

# Output the best result
print(f"Best parameters: {best_params}")
print(f"Best profit: {best_profit:.2f}")
