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

# Import strategies
from mean_reversion import strategy
from buyHold import BuyHoldStrategy

class Alpaca_trader:
    def __init__(self) -> None:
        self.strategy = BuyHoldStrategy()
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


    def submit_buy_order(self, symbol: str, qty: int):

        buy_tickers = self.strategy.get_buy_tickers() 
        if self.is_market_open():
             print("Market is open!")
             eligible_symbols = buy_tickers
        else:
            eligible_symbols = [symbol for symbol in buy_tickers if '-USD' in symbol]
        

        for symbol in eligible_symbols:
            try:
                buy_order = self.api.submit_order(
                    symbol=symbol,       # Stock symbol
                    qty=qty,             # Number of shares
                    side='buy',          # 'buy' or 'sell'
                    type='market',       # Order type
                    time_in_force='gtc'  # Good 'til canceled
                )
                print(f"Buy order submitted: {buy_order}")
            except Exception as e:
                print(f"Error submitting order: {e}")


    def submit_sell_order(self, symbol: str, qty: int):
        positions = self.get_portfolio()
        positions = self.positions['asset'].tolist()  #

        sell_tickers = self.strategy.get_sell_tickers() 
        if self.is_market_open():
             print("Market is open!")
             eligible_symbols = [symbol for symbol in sell_tickers if symbol in positions]
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


if __name__ == "__main__":
    # Initialize the strategy with a ticker (e.g., MSFT)
    strategy = BuyHoldStrategy()
    tickers_to_buy = strategy.get_buy_tickers()
    tickers_to_sell = strategy.get_sell_tickers()

    # Initialize the Alpaca trader
    trader = Alpaca_trader()
    # Optionally, you can check the portfolio after placing the order
    trader.get_portfolio()

    # Loop through the tickers and place buy orders
    for ticker in tickers_to_buy:
        # Here we assume you want to buy 1 share; adjust 'qty' as needed
        trader.submit_buy_order(symbol=ticker, qty=1)
    
    for ticker in tickers_to_sell:
        trader.submit_sell_order(symbol=ticker, qty=1)
    

    
    

