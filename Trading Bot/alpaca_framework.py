import os
import pandas as pd
import yfinance as yf
import alpaca_trade_api as tradeapi
import configparser
import pytz
import locale
import pandas_market_calendars as mcal
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from ta.trend import sma_indicator
from tqdm import tqdm
from requests_html import HTMLSession
from datetime import datetime
import logging


class Alpaca_trader:
    def __init__(self) -> None:
        print(f"Initializing Alpaca API with endpoint:...")
        API_KEY = "PKDGHHFCJZROI1ECN5O4"
        API_SECRET = "VB5wbJjCJwmDscz0QnadNz3mTw19lgRhi2XRysis"
        BASE_URL = "https://paper-api.alpaca.markets"  # Or use the live URL if not in paper trading mode

        self.api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
        print(f"API initialized: {self.api}")

    def get_portfolio(self):    
        print("Getting Positions")
        self.positions = pd.DataFrame({
            'asset': [x.symbol for x in self.api.list_positions()],
            'current_price': [x.current_price for x in self.api.list_positions()],
            'qty': [x.qty for x in self.api.list_positions()],
            'market_value': [x.market_value for x in self.api.list_positions()],
            'profit_dol': [x.unrealized_pl for x in self.api.list_positions()],
            'profit_pct': [x.unrealized_plpc for x in self.api.list_positions()]
        })
        print(self.positions)

        # Cache account data to avoid redundant API calls
        account = self.api.get_account()   

        self.cash = pd.DataFrame({
            'asset': 'Cash',
            'current_price': self.api.get_account().cash,
            'qty': self.api.get_account().cash,
            'market_value': self.api.get_account().cash,
            'profit_dol': 0,
            'profit_pct': 0
        }, index=[0])  # Set index=[0] since passing scalars in DataFrame
        print(self.cash)

        return self.positions, self.cash

    
    @staticmethod
    def is_market_open():
        nyse = pytz.timezone('America/New_York')
        current_time = datetime.now(nyse)

        nyse_calendar = mcal.get_calendar('NYSE')
        market_schedule = nyse_calendar.schedule(start_date=current_time.date(), end_date=current_time.date())

        if not market_schedule.empty:  # Corrected this line
            market_open = market_schedule.iloc[0]['market_open'].to_pydatetime().replace(tzinfo=None)
            market_close = market_schedule.iloc[0]['market_close'].to_pydatetime().replace(tzinfo=None)
            current_time_no_tz = current_time.replace(tzinfo=None)
 
            if market_open <= current_time_no_tz <= market_close:
                return True

        return False


    def submit_buy_order(self, ticker: str, qty: int):

        if self.is_market_open():
             print("Market is open!")
             eligible_symbols = ticker
        else:
            eligible_symbols = []
        
        purchases = []
        for symbol in eligible_symbols:
            try:
                buy_order = self.api.submit_order(
                    symbol=symbol,       # Stock symbol
                    qty= '1',             # Number of shares
                    side='buy',          # 'buy' or 'sell'
                    type='market',       # Order type
                    time_in_force='gtc'  # Good 'til canceled
                )
                print(f"Buy order submitted: {buy_order}")
                purchases.append([symbol, round(qty)])
                logging.info(f"Purchased: {symbol} at {datetime.now()}")
            except Exception as e:
                print(f"Error submitting order: {e}")


    def submit_sell_order(self, ticker: str, qty: int):
        positions = self.get_portfolio()
        positions = self.positions['asset'].tolist()  #


        if self.is_market_open():
             print("Market is open!")
             eligible_symbols = ticker
        else:
            eligible_symbols = [] 
        
        executed_sales = []
        for symbol in eligible_symbols:  
            try:
                sell_order = self.api.submit_order(
                        symbol=symbol,       # Stock symbol
                        qty=qty,             # Number of shares
                        side='sell',         # 'buy' or 'sell'
                        type='market',       # Order type
                        time_in_force='gtc'  # Good 'til canceled
                    )
                executed_sales.append([symbol, round(qty)])
                print(f"Sell order submitted: {sell_order}")
            except Exception as e:
                print(f"Error submitting order: {e}")
            return

