import pandas as pd
from requests_html import HTMLSession
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator
from tqdm import tqdm

class strategy:

    def __init__(self, rsi_window=10):
        self.n_stocks = 50
        self.fibonacci_sequence = [5, 8, 13]
        self.rsi_window = rsi_window
        self.rsi_oversold = 30

    def get_daily_losers(self):
        # Yahoo Finance daily losers URL
        daily_losers = "https://finance.yahoo.com/losers?offset=0&count=100"

        # Create an HTML session to fetch data
        session = HTMLSession()
        response = session.get(daily_losers)

        # Parse the response and get the data table
        tables = pd.read_html(response.html.raw_html)
        df = tables[0].copy()

        # Only get the number of stocks specified by n_stocks
        df = df.head(self.n_stocks).reset_index(drop=True)

        # Extract just the ticker from the "Symbol" column
        self.tickers = df["Symbol"].apply(lambda x: x.split()[0])

        # Close the session after the data is fetched
        session.close()
        return self.tickers
    
    def get_ticker_info(self, df=None):
        if df is None:
            tickers = self.tickers
        else:
            tickers = list(df["yf_ticker"])

        df_indicators = []

        for symbol in tqdm(
            tickers,
            desc="• Grabbing technical metrics for " + str(len(tickers)) + " tickers",
        ):
            try:
                Ticker = yf.Ticker(symbol)
                Hist = Ticker.history(period="ytd", interval='1d')
                
                # Calculate SMA for the ticker
                for n in self.fibonacci_sequence:
                    Hist["ma" + str(n)] = sma_indicator(close=Hist["Close"], window=n, fillna=False)
                
                # Calculate RSI with the specified window
                Hist["rsi" + str(self.rsi_window)] = RSIIndicator(close=Hist["Close"], window=self.rsi_window).rsi()
                
                # Get the most recent 15 days of data
                df_indicators_temp = Hist.iloc[-15:].reset_index(drop=True)
                df_indicators_temp.insert(0, "Symbol", Ticker.ticker)
                df_indicators_temp["trend"] = "Neutral"  # Initialize trend column
                df_indicators.append(df_indicators_temp)
            
            except KeyError as e:
                print(f"KeyError for {symbol}: {e}")
                continue

        # Remove empty dataframes and concatenate
        df_indicators = [x for x in df_indicators if not x.empty]
        df_indicators = pd.concat(df_indicators)

        # Determine the trend based on SMA values
        if not df_indicators.empty:
            # Use element-wise logical operations and proper pandas methods
            buy_criteria = (
                (df_indicators['ma5'] > df_indicators['ma8']) &
                (df_indicators['ma8'] > df_indicators['ma13'])
            ) | (df_indicators['rsi' + str(self.rsi_window)] < self.rsi_oversold)
            
            # Filter the DataFrame
            buy_filtered_df = df_indicators[buy_criteria]

            # Create a list of tickers to trade
            self.buy_tickers = list(buy_filtered_df["Symbol"])

            return buy_filtered_df  # Return DataFrame with indicators and trends

