import yfinance as yf
import pandas as pd
from fredapi import Fred
import logging
import datetime as dt

# Global variables
logging.basicConfig(filename='dcf_analysis.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', '{:.2f}'.format)

years = 5
fred_api_key = '4978884d3d995014011229a1d6b98f1b'  

def get_ticker():
    return input("What Ticker would you like to view?: ").strip().upper()


def calculate_wacc(ticker):
    try:
        print(f"Calculating WACC for {ticker}...")
        balance_sheet = yf.Ticker(ticker).balancesheet.iloc[:, 0:4].iloc[:, ::-1]
        income_statement = yf.Ticker(ticker).financials.iloc[:, 0:4].iloc[:, ::-1]

        end_date = dt.datetime.now()
        start_date = end_date - dt.timedelta(days=365 * 10)
        historical_data = yf.download(ticker, start=start_date, end=end_date)
        sp500_data = yf.download('^GSPC', start=start_date, end=end_date)

        stock_adj_close = historical_data['Adj Close']
        index_adj_close = sp500_data['Adj Close']

        stock_returns = stock_adj_close.pct_change().dropna()
        index_returns = index_adj_close.pct_change().dropna()

        combined = pd.concat([stock_returns, index_returns], axis=1).dropna()
        stock_returns = combined.iloc[:, 0]
        index_returns = combined.iloc[:, 1]

        covariance = stock_returns.cov(index_returns)
        variance = index_returns.var()
        beta = covariance / variance    

        fred = Fred(api_key=fred_api_key)
        ten_year_treasury_rate = fred.get_series_latest_release('GS10') / 100
        risk_free_rate = ten_year_treasury_rate.iloc[-1]

        trading_days_per_year = 252
        cumulative_return_sp500 = (index_adj_close.iloc[-1] / index_adj_close.iloc[0]) - 1
        avg_annual_return_sp500 = (1 + cumulative_return_sp500) ** (1 / (len(index_adj_close) / trading_days_per_year)) - 1

        risk_premium = avg_annual_return_sp500 - risk_free_rate
        cost_of_equity = risk_free_rate + beta * risk_premium

        current_ticker_price = stock_adj_close.iloc[-1]
        market_value_of_equity = current_ticker_price * (yf.Ticker(ticker).info.get("sharesOutstanding"))

        total_debt = balance_sheet.loc['Total Debt'].values[0]
        market_value_of_debt = total_debt

        total_market_value = market_value_of_equity + market_value_of_debt
        weight_of_equity = market_value_of_equity / total_market_value
        weight_of_debt = market_value_of_debt / total_market_value
        after_tax_cost_of_debt = (income_statement.loc['Interest Expense'].values[0] / total_debt) * (1 - 0.2)
        WACC = (weight_of_equity * cost_of_equity) + (weight_of_debt * after_tax_cost_of_debt)

        print(f"Beta: {beta}")
        print(f"Risk Free Rate: {risk_free_rate}")
        print(f"Weight of Equity: {weight_of_equity}")
        print(f"Cost of Equity: {cost_of_equity}")
        print(f"Weight of Debt: {weight_of_debt}")
        print(f"Cost of Debt: {after_tax_cost_of_debt}")
        print(f"WACC for {ticker}: {WACC}")

        return WACC
    except Exception as e:
        logging.error(f"Error calculating WACC for {ticker}: {e}")
        return None

def main():
    ticker  = get_ticker()
    wacc = calculate_wacc(ticker)
    
if __name__ == "__main__":
    main()

