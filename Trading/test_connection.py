import alpaca_trade_api as tradeapi
import pandas as pd

API_KEY = "PKDGHHFCJZROI1ECN5O4"
API_SECRET = "VB5wbJjCJwmDscz0QnadNz3mTw19lgRhi2XRysis"
BASE_URL = "https://paper-api.alpaca.markets"  # Or use the live URL if not in paper trading mode

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')



positions = pd.DataFrame({
               'asset': [x.symbol for x in api.list_positions()],
                'current_price': [x.current_price for x in api.list_positions()],
                'qty': [x.qty for x in api.list_positions()],
                'market_value': [x.market_value for x in api.list_positions()],
                'profit_dol': [x.unrealized_pl for x in api.list_positions()],
                'profit_pct': [x.unrealized_plpc for x in api.list_positions()]
        })

print(positions)

cash = pd.DataFrame({
                'asset': 'Cash',
                'current_price': api.get_account().cash,
                'qty': api.get_account().cash,
                'market_value': api.get_account().cash,
                'profit_dol': 0,
                'profit_pct': 0
            }, index=[0])  # Need to set index=[0] since passing scalars in df

print(cash)