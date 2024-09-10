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

from mean_reversion import Strategy


class Alpaca:
    def __init__(self) -> None:
        config = configparser.ConfigParser()
        config.read('config.ini')

        API_KEY = config['alpaca']['api_key']
        API_SECRET = config['alpaca']['api_secret']
        ENDPOINT = config['alpaca']['endpoint']

        self.api = tradeapi.REST(
            key_id=API_KEY,
            secret_key=API_SECRET,
            base_url=ENDPOINT
        )

    #fetch the account portfolio, this includes both cash and positions.
    def get_current_portfolio(self):
        positions = pd.DataFrame(
            {
                'asset': [x.symbol for x in self.api.list_positions()],
                'current_price': [x.current_price for x in self.api.list_positions()],
                'qty': [x.qty for x in self.api.list_positions()],
                'market_value': [x.market_value for x in self.api.list_positions()],
                'profit_dol': [x.unrealized_pl for x in self.api.list_positions()],
                'profit_pct': [x.unrealized_plpc for x in self.api.list_positions()]
            }
        )

        cash = pd.DataFrame(
            {
                'asset': 'Cash',
                'current_price': float(self.api.get_account().cash),
                'qty': float(self.api.get_account().cash),
                'market_value': float(self.api.get_account().cash),
                'profit_dol': 0,
                'profit_pct': 0
            },
            index=[0]  # Set index=[0] since passing scalars in DataFrame
        )

        assets = pd.concat([positions, cash], ignore_index=True)
        float_assets = ['current_price', 'qty', 'market_value', 'profit_dol', 'profit_pct']
        assets[float_assets] = assets[float_assets].astype(float)

        return assets

    #This function ensures the market is open when the program tries to submit buy and sell requests
    @staticmethod
    def is_market_open():
        nyse = pytz.timezone('America/New_York')
        current_time = datetime.now(nyse)

        nyse_calendar = mcal.get_calendar('NYSE')
        market_schedule = nyse_calendar.schedule(start_date=current_time.date(), end_date=current_time.date())

        if not market_schedule.empty():
            market_open = market_schedule.iloc[0]['market_open'].to_pydatetime().replace(tzinfo=None)
            market_close = market_schedule.iloc[0]['market_close'].to_pydatetime().replace(tzinfo=None)
            current_time_no_tz = current_time.replace(tzinfo=None)

            if market_open <= current_time_no_tz <= market_close:
                return True

        return False


    #Function to execute a buy order, it takes the strategy and then sumbits the buy request to alpaca based on the strategy 
    def sell_order(self):
        # Get the current time in Eastern Time
        et_tz = pytz.timezone('US/Eastern')
        current_time = datetime.now(et_tz)

        # Define trade opportunities using the Strategy class
        TradeOpps = Strategy()

        # Get current portfolio
        df_current_positions = self.get_current_portfolio()

        # Filter out Cash and get historical data for current positions
        df_current_positions_hist = TradeOpps.get_asset_info(
            df=df_current_positions[df_current_positions['asset'] != 'Cash']
        )

        # Define sell criteria based on strategy
        sell_criteria = TradeOpps.get_ticker_info(df_current_positions_hist)

        # Filter DataFrame based on sell criteria
        sell_filtered_df = df_current_positions_hist[sell_criteria]
        sell_filtered_df['alpaca_symbol'] = sell_filtered_df['Symbol'].str.replace('-', '')
        symbols = list(sell_filtered_df['alpaca_symbol'])

        # Determine eligible symbols
        if self.is_market_open():
            eligible_symbols = symbols
        else:
            eligible_symbols = [symbol for symbol in symbols if "-USD" in symbol]

        # Execute sales
        executed_sales = []
        for symbol in eligible_symbols:
            try:
                if symbol in symbols:
                    print(f"• Selling {symbol}")
                    qty = df_current_positions[df_current_positions['asset'] == symbol]['qty'].values[0]
                    self.api.submit_order(
                        symbol=symbol,
                        time_in_force='gtc',
                        qty=qty,
                        side="sell"
                    )
                    executed_sales.append([symbol, round(qty)])
            except Exception as e:
                print(f"Error selling {symbol}: {e}")
                logging.error(f"Error selling {symbol}: {e}")  # Log errors
                continue

        executed_sales_df = pd.DataFrame(executed_sales, columns=['ticker', 'quantity'])

        # Check if eligible_symbols were empty and log
        if len(eligible_symbols) == 0:
            self.sold_message = "• liquidated no positions based on the sell criteria"
        else:
            self.sold_message = f"• executed sell orders for {''.join([symbol + ', ' if i < len(eligible_symbols) - 1 else 'and ' + symbol for i, symbol in enumerate(eligible_symbols)])}based on the sell criteria"

        print(self.sold_message)

        # Check if Cash is at least 10% of total holdings
        cash_row = df_current_positions[df_current_positions['asset'] == 'Cash']
        total_holdings = df_current_positions['market_value'].sum()

        if cash_row['market_value'].values[0] / total_holdings < 0.1:
            # Sort by profit_pct and rebalance top-performing assets
            df_current_positions = df_current_positions.sort_values(by=['profit_pct'], ascending=False)
            top_half = df_current_positions.iloc[:len(df_current_positions) // 4]
            top_half_market_value = top_half['market_value'].sum()
            cash_needed = total_holdings * 0.1 - cash_row['market_value'].values[0]

            for index, row in top_half.iterrows():
                print(f"• selling {row['asset']} for 10% portfolio cash requirement")
                amount_to_sell = int((row['market_value'] / top_half_market_value) * cash_needed)
                try:
                    self.api.submit_order(
                        symbol=row['asset'],
                        qty=amount_to_sell,
                        side="sell",
                        time_in_force="gtc"
                    )
                except Exception as e:
                    print(f"Error selling {row['asset']}: {e}")
                    logging.error(f"Error selling {row['asset']}: {e}")

            try:
                # Set locale to US
                locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

                # Convert cash_needed to a string with dollar sign and commas
                cash_needed_str = locale.currency(cash_needed, grouping=True)
                print(f"• Sold {cash_needed_str} of top 25% of performing assets to reach 10% cash position")
            except locale.Error as e:
                print(f"Error setting locale: {e}")
                logging.error(f"Error setting locale: {e}")

        return executed_sales_df

 #Function effeectivley does the same as the sell but opposite, it takes the strategy and then sumbits the sell request to alpaca based on the strategy 
    def buy_orders(self, tickers):
        df_current_positions = self.get_current_portfolio()
        available_cash = df_current_positions[df_current_positions['asset'] == 'Cash']['market_value'].values[0]

        # Get the current time in Eastern Time
        et_tz = pytz.timezone('US/Eastern')
        current_time = datetime.now(et_tz)

        if self.is_market_open():
            eligible_symbols = tickers
        else:
            eligible_symbols = [symbol for symbol in tickers if '-USD' in symbol]

        # Submit buy orders for eligible symbols
        for symbol in eligible_symbols:
            try:
                self.api.submit_order(
                    symbol=symbol,
                    time_in_force='gtc',
                    notional=available_cash / len(eligible_symbols),
                    side="buy"
                )
            except Exception as e:
                print(f"Error buying {symbol}: {e}")
                logging.error(f"Error buying {symbol}: {e}")

        if len(eligible_symbols) == 0:
            self.bought_message = "• executed no buy orders based on the buy criteria"
        else:
            self.bought_message = f"• executed buy orders for {''.join([symbol + ', ' if i < len(eligible_symbols) - 1 else 'and ' + symbol for i, symbol in enumerate(eligible_symbols)])}based on the buy criteria"

        print(self.bought_message)
        self.tickers_bought = eligible_symbols
