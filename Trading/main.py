
import datetime
from mean_reversion import *
from alpaca_framework import *
from test_strat import *


def main():
    config = configparser.ConfigParser()
    config.read("config.ini")

    API_KEY = config['alpaca']['api_key']
    API_SECRET = config['alpaca']['api_secret']
    ENDPOINT = config['alpaca']['endpoint'].strip('"')  # Remove any extra quotes

    # Instantiate Alpaca class with the expected parameters
    Alpaca_instance = Alpaca(API_KEY, API_SECRET, ENDPOINT)

    api = tradeapi.REST(
        key_id=API_KEY,
        secret_key=API_SECRET,
        base_url=ENDPOINT,
    )

    trades = strategy()
    trades.get_daily_losers()

    # The all_tickers attribute is a list of all tickers in the get_trading_opportunities() method. Passing this list through the get_asset_info() method shows just the tickers that meet buying criteria
    trades.get_ticker_info()

    # Liquidates currently held assets that meet sell criteria and stores sales in a df
    Alpaca_instance.sell_order()

    # Execute buy_orders using trades.buy_tickers and stores buys in a tickers_bought list
    Alpaca_instance.buy_orders(tickers=trades.buy_tickers)
    Alpaca_instance.tickers_bought

    current_time = datetime.now(pytz.timezone("CET"))
    current_time = datetime.now(pytz.timezone("CET"))
    hour = current_time.hour



if __name__ == "__main__":
    main()
