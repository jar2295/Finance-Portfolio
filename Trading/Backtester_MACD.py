import os
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator, ema_indicator
from tqdm import tqdm
import matplotlib.pyplot as plt

# Configuration Parameters
TICKERS = ['SPY']  # List of tickers to backtest
INTERVAL = '1m'  # Data interval for backtesting
PERIOD = "5d"  # Period for data
INITIAL_BALANCE = 1000  # Initial balance for backtesting

# Indicators Parameters

BB_WINDOW = 20  # Window for Bollinger Bands (SMA)
BB_STD_DEV = 2  # Standard deviation for Bollinger Bands

class Backtester:
    def __init__(self, tickers, initial_balance, interval):
        self.tickers = tickers
        self.initial_balance = initial_balance
        self.data = {}
        self.interval = interval
        self.running = True
        
    def fetch_data(self):
        """Fetch historical data for each ticker."""
        for symbol in tqdm(self.tickers, desc="• Fetching data for tickers"):
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=PERIOD, interval=self.interval)
                if data.empty:
                    print(f"No data found for {symbol}")
                    continue
                data = data.sort_index()
                self.data[symbol] = data
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
    
    def compute_indicators(self):
        """Compute the indicators for each ticker."""
        for symbol, data in self.data.items():
            if data.empty:
                continue
            
            # Calculate MACD and Signal line
            data['EMA_12'] = data['Close'].ewm(span=12, adjust=False).mean()
            data['EMA_26'] = data['Close'].ewm(span=26, adjust=False).mean()
            data['MACD'] = data['EMA_12'] - data['EMA_26']
            data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
            data['MACD_Histogram'] = data['MACD'] - data['Signal']

            # Calculate Bollinger Bands
            data['BB_Mid'] = data['Close'].rolling(window=BB_WINDOW).mean()
            data['BB_STD'] = data['Close'].rolling(window=BB_WINDOW).std()
            data['BB_Upper'] = data['BB_Mid'] + (data['BB_STD'] * BB_STD_DEV)
            data['BB_Lower'] = data['BB_Mid'] - (data['BB_STD'] * BB_STD_DEV)
            
            # Calculate RSI
            rsi_indicator = RSIIndicator(data['Close'])
            data['RSI'] = rsi_indicator.rsi()
            
            self.data[symbol] = data.dropna()

    def backtest(self):
        """Simulate trading based on MACD signals and calculate profitability."""
        results = {}
        for symbol, data in self.data.items():
            if data.empty:
                continue
            
            # Initialize trading variables
            cash = self.initial_balance
            position = 0
            last_trade_price = 0
            
            # Initialize columns for trade signals
            data['MACD_Trade'] = 0  # +1 for buy, -1 for sell
            data['Position'] = 0  # Current position in terms of units
            data['Portfolio_Value'] = cash
            
            # Iterate through the data to generate signals and track trades
            for i in range(1, len(data)):
                macd_current = data['MACD'].iloc[i]
                macd_previous = data['MACD'].iloc[i - 1]
                signal_current = data['Signal'].iloc[i]
                signal_previous = data['Signal'].iloc[i - 1]
                price = data['Close'].iloc[i]

                # Generate buy signal
                if macd_previous < signal_previous and macd_current > signal_current:
                    if cash > 0:  # Buy if we have cash
                        position = cash / price
                        cash = 0
                        last_trade_price = price
                        data.at[data.index[i], 'MACD_Trade'] = 1  # Buy signal
                
                # Generate sell signal
                elif macd_previous > signal_previous and macd_current < signal_current:
                    if position > 0:  # Sell if we have a position
                        cash = position * price
                        position = 0
                        last_trade_price = price
                        data.at[data.index[i], 'MACD_Trade'] = -1  # Sell signal

                # Update portfolio value
                data.at[data.index[i], 'Position'] = position
                data.at[data.index[i], 'Portfolio_Value'] = cash + (position * price)
            
            # Store results for plotting
            results[symbol] = data
            # Calculate final balance and profit
            final_balance = cash + (position * data['Close'].iloc[-1])
            profit = final_balance - self.initial_balance
            print(f"Final Balance for {symbol}: ${final_balance:.2f}")
            print(f"Profit for {symbol}: ${profit:.2f}")
   


    def run(self):
            backtester.fetch_data()

            while self.running:
                backtester.compute_indicators()
                backtester.backtest()
                            

if __name__ == "__main__":
    backtester = Backtester(TICKERS, INITIAL_BALANCE, INTERVAL)
    backtester.run()
    
