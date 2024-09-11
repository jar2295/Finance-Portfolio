import pandas as pd
from requests_html import HTMLSession
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator
from tqdm import tqdm
import pandas as pd
import numpy as np


class Strategy: 
    def __init__(self) -> None:
        self.fibonacci = [5, 8, 13, 21, 34]
        self.BB_upper = 1.618  # Use numerical value instead of string
        self.bb_lower = 1.618  # Use numerical value instead of string
        self.rsi_period = 14   # Set default RSI period
        self.rsi_upper = 70    # Set default RSI upper threshold
        self.rsi_lower = 30    # Set default RSI lower threshold
        self.data = {}         # To store data for each ticker
        
    def get_potential_tickers(self):
        self.tickers = ["aapl"]
        return self.tickers

    def get_ticker_info(self):
        
            
        df_indicators = []

        for symbol in tqdm(
            self.tickers,
            desc="• Grabbing technical metrics for " + str(len(self.tickers)) + " tickers",
        ):    
            try:
                Ticker = yf.Ticker(symbol)
                data = Ticker.history(period="5d", interval='5m')
                data = data.sort_index()
                if data.empty:
                    print(f"No data found for {symbol}")
                    continue

                for n in self.fibonacci:
                    data[f'SMA{n}'] = data['Close'].rolling(window=n).mean()

            
            except KeyError as e:
                print(f"KeyError for {symbol}: {e}")
                continue

   
if __name__ == "__main__":
    strategy = Strategy()  # Initialize the strategy
    strategy.get_potential_tickers()  # Get potential tickers
    strategy.get_ticker_info()  # Fetch data and compute indicators

