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
from test_strat import BuyHoldStrategy


# Strategy selection
STRATEGY_TYPE = 'BuyHold'  # Change this to 'MeanReversion' or 'BuyHold'

class Alpaca:
    def __init__(self, API_KEY, API_SECRET, ENDPOINT) -> None:
        self.api = tradeapi.REST(
            key_id=API_KEY,
            secret_key=API_SECRET,
            base_url=ENDPOINT
        )

        self.strategy = strategy  # Default value, you can set this later
        self.tickers_bought = []
        self.bought_message = ""
        self.sold_message = ""
        


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
            index=[0]
        )

        assets = pd.concat([positions, cash], ignore_index=True)
        float_assets = ['current_price', 'qty', 'market_value', 'profit_dol', 'profit_pct']
        assets[float_assets] = assets[float_assets].astype(float)

        return assets

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

    def sell_order(self):
        et_tz = pytz.timezone('US/Eastern')
        current_time = datetime.now(et_tz)

        df_current_positions = self.get_current_portfolio()
        df_current_positions['yf_ticker'] = df_current_positions['asset']

        # Call strategy's sell method if implemented
        if hasattr(self.strategy, 'get_sell_tickers'):
            sell_criteria = self.strategy.get_sell_tickers(df_current_positions)
            logging.info(f"Sell criteria: {sell_criteria}")
            sell_filtered_df = df_current_positions[df_current_positions['asset'].isin(sell_criteria)]
            sell_filtered_df['alpaca_symbol'] = sell_filtered_df['asset'].str.replace('-', '')
            symbols = list(sell_filtered_df['alpaca_symbol'])
            logging.info(f"Symbols to sell: {symbols}")

            if self.is_market_open():
                eligible_symbols = symbols
            else:
                eligible_symbols = [symbol for symbol in symbols if "-USD" in symbol]

            executed_sales = []
            for symbol in eligible_symbols:
                try:
                    if symbol in symbols:
                        qty = df_current_positions[df_current_positions['asset'] == symbol]['qty'].values[0]
                        self.api.submit_order(
                            symbol=symbol,
                            time_in_force='gtc',
                            qty=qty,
                            side="sell"
                        )
                        executed_sales.append([symbol, round(qty)])
                        logging.info(f"Sold {symbol}, quantity: {qty}")
                except Exception as e:
                    logging.error(f"Error selling {symbol}: {e}")
                    continue

            executed_sales_df = pd.DataFrame(executed_sales, columns=['ticker', 'quantity'])

            if len(eligible_symbols) == 0:
                self.sold_message = "• liquidated no positions based on the sell criteria"
            else:
                self.sold_message = f"• executed sell orders for {', '.join(eligible_symbols)} based on the sell criteria"

            logging.info(self.sold_message)

            cash_row = df_current_positions[df_current_positions['asset'] == 'Cash']
            total_holdings = df_current_positions['market_value'].sum()

            if cash_row['market_value'].values[0] / total_holdings < 0.1:
                df_current_positions = df_current_positions.sort_values(by=['profit_pct'], ascending=False)
                top_half = df_current_positions.iloc[:len(df_current_positions) // 4]
                top_half_market_value = top_half['market_value'].sum()
                cash_needed = total_holdings * 0.1 - cash_row['market_value'].values[0]

                for index, row in top_half.iterrows():
                    amount_to_sell = int((row['market_value'] / top_half_market_value) * cash_needed)
                    try:
                        self.api.submit_order(
                            symbol=row['asset'],
                            qty=amount_to_sell,
                            side="sell",
                            time_in_force="gtc"
                        )
                        logging.info(f"Sold {row['asset']} to reach 10% cash, quantity: {amount_to_sell}")
                    except Exception as e:
                        logging.error(f"Error selling {row['asset']}: {e}")

                try:
                    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                    cash_needed_str = locale.currency(cash_needed, grouping=True)
                    logging.info(f"Sold {cash_needed_str} of top 25% of performing assets to reach 10% cash position")
                except locale.Error as e:
                    logging.error(f"Error setting locale: {e}")

            return executed_sales_df

    def buy_orders(self):
        df_current_positions = self.get_current_portfolio()
        available_cash = df_current_positions[df_current_positions['asset'] == 'Cash']['market_value'].values[0]

        # Call strategy's buy method
        tickers = self.strategy.get_buy_tickers()
        logging.info(f"Buying tickers: {tickers}")

        if self.is_market_open():
            eligible_symbols = tickers
        else:
            eligible_symbols = [symbol for symbol in tickers if '-USD' in symbol]

        for symbol in eligible_symbols:
            try:
                self.api.submit_order(
                    symbol=symbol,
                    time_in_force='gtc',
                    notional=available_cash / len(eligible_symbols),
                    side="buy",
                    qty=1  # Buy only 1 share of the stock
                )
                logging.info(f"Bought {symbol}, notional: {available_cash / len(eligible_symbols)}")
            except Exception as e:
                logging.error(f"Error buying {symbol}: {e}")

        if len(eligible_symbols) == 0:
            self.bought_message = "• executed no buy orders based on the buy criteria"
        else:
            self.bought_message = f"• executed buy orders for {', '.join(eligible_symbols)} based on the buy criteria"

        logging.info(self.bought_message)
        self.tickers_bought = eligible_symbols

