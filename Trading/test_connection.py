import alpaca_trade_api as tradeapi

API_KEY = "PK16CGQJW3B315HPYZJQ"
API_SECRET = "KYvcjnK3oUrco5bHhFsUmpgOub4gdAeGHOYvtO5P"
BASE_URL = "https://paper-api.alpaca.markets"  # Or use the live URL if not in paper trading mode

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

try:
    account = api.get_account()
    print(f"Account status: {account.status}")
except tradeapi.rest.APIError as e:
    print(f"APIError: {e}")
