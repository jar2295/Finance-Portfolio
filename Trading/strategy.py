import pandas as pd

import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator
from tqdm import tqdm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


class Strategy: 
    def __init__(self) -> None:
        self.fibonacci = [5, 8, 13, 21, 34]
        self.std_dev_multiplier = 1.618  # Use numerical value instead of string
        self.bb_window = 10
        self.rsi_period = 14   # Set default RSI period
        self.rsi_upper = 70    # Set default RSI upper threshold
        self.rsi_lower = 30    # Set default RSI lower threshold
        self.rsi_window = 10
        self.data = {}         # To store data for each ticker
        
    def get_potential_tickers(self):
        self.tickers = ["aapl"]
        return self.tickers

    def get_ticker_info(self):

        for symbol in tqdm(
            self.tickers,
            desc="• Grabbing technical metrics for " + str(len(self.tickers)) + " tickers",
        ):    
            try:
                Ticker = yf.Ticker(symbol)
                data = Ticker.history(period="1d", interval='1m')
                data = data.sort_index()
                if data.empty:
                    print(f"No data found for {symbol}")
                    continue

                for n in self.fibonacci:
                    data["SMA"] = data['Close'].rolling(window=n).mean()

                rsi= RSIIndicator(close=data["Close"], window=self.rsi_window).rsi()
                data['RSI'] = rsi

                data['SMA_BB'] = data['Close'].rolling(window= self.bb_window).mean()
                data['Rolling Std Dev'] = data['Close'].rolling(window=self.bb_window).std()
                data['Upper Band'] = data["SMA"] + (data['Rolling Std Dev'] * self.std_dev_multiplier)
                data['Lower Band'] = data['SMA'] - (data['Rolling Std Dev'] * self.std_dev_multiplier)

                self.data[symbol] = data.dropna()

                return self.data
            
            except KeyError as e:
                print(f"KeyError for {symbol}: {e}")
                continue




    def plot(self):
        for symbol, data in self.data.items():
            plt.figure(figsize=(14, 7))
            
            # Debug: Print columns and sample data for plotting
            print(f"Columns for plotting {symbol}: {data.columns}")
            print(f"Sample data for plotting {symbol}:")
            print(data.head())
            
            # Plot Close Price and SMAs
            if 'Close' in data.columns:
                plt.plot(data.index, data['Close'], label='Close Price', color='black')
            else:
                print(f"'Close' column not found in data for {symbol}")
            
            for n in self.fibonacci:
                if f'SMA{n}' in data.columns:
                    plt.plot(data.index, data[f'SMA{n}'], label=f'SMA{n}')
                else:
                    print(f"SMA{n} column not found in data for {symbol}")
                    
            # Plot Bollinger Bands
            if 'Upper Band' in data.columns and 'Lower Band' in data.columns:
                plt.plot(data.index, data['Upper Band'], label='Upper Band', color='red', linestyle='--')
                plt.plot(data.index, data['Lower Band'], label='Lower Band', color='red', linestyle='--')
                plt.plot(data.index, data['SMA_BB'], label='Middle Band', color='blue', linestyle='--')
            else:
                print(f"Bollinger Bands columns not found in data for {symbol}")
            
            plt.title(f'{symbol} - Bollinger Bands & SMAs')
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.legend()
            plt.grid()
            plt.show()

        

   
if __name__ == "__main__":
    strategy = Strategy()  # Initialize the strategy
    strategy.get_potential_tickers()  # Get potential tickers
    strategy.get_ticker_info()  # Fetch data and compute indicators
    strategy.plot()

