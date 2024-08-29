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
fred_api_key = '4978884d3d995014011229a1d6b98f1b'  # Replace with your actual FRED API key

def get_ticker():
    return input("What Ticker would you like to view?: ").strip().upper()

def parse(ticker):
    try:
        print(f"Parsing data for {ticker}...")
        ticker_data = yf.Ticker(ticker) 
        cashflow_statement = ticker_data.cash_flow.iloc[:, 0:4].iloc[:, ::-1]  # Reverse the columns
        historical_cash_flows = cashflow_statement.loc["Free Cash Flow"].astype(float)
        shares_outstanding = ticker_data.info.get("sharesOutstanding")

        print(f"Ticker: {ticker}, Free Cash Flows: {historical_cash_flows}, Shares Outstanding: {shares_outstanding}")
        
        return cashflow_statement, historical_cash_flows, shares_outstanding
    except Exception as e:
        logging.error(f"Error parsing data for {ticker}: {e}")
        return None, None, None

def calculate_wacc(ticker, shares_outstanding):
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
        market_value_of_equity = current_ticker_price * shares_outstanding

        total_debt = balance_sheet.loc['Total Debt'].values[0]
        market_value_of_debt = total_debt

        total_market_value = market_value_of_equity + market_value_of_debt
        weight_of_equity = market_value_of_equity / total_market_value
        weight_of_debt = market_value_of_debt / total_market_value
        after_tax_cost_of_debt = (income_statement.loc['Interest Expense'].values[0] / total_debt) * (1 - 0.2)
        WACC = (weight_of_equity * cost_of_equity) + (weight_of_debt * after_tax_cost_of_debt)

        print(f"WACC for {ticker}: {WACC}")

        return WACC
    except Exception as e:
        logging.error(f"Error calculating WACC for {ticker}: {e}")
        return None

def get_growth():
    try:
        cashflow_growth = float(input("What growth rate do you expect for Cash Flows?: ").strip())
        terminal_growth = float(input("What growth do you expect in the terminal period?: ").strip())
        return cashflow_growth, terminal_growth
    except ValueError:
        logging.error("Invalid input for growth rates. Please enter numeric values.")
        return None, None

def dcf(ticker, WACC, historical_cash_flows, shares_outstanding, terminal_growth, cashflow_growth):
    try:
        print(f"Calculating DCF for {ticker}...")
        most_recent_cash_flow = historical_cash_flows.iloc[-1]
        forecasted_cash_flows = [most_recent_cash_flow]
        for i in range(1, years):
            forecasted_cash_flows.append(forecasted_cash_flows[-1] * (1 + cashflow_growth))

        if terminal_growth >= WACC:
            print(f"Growth rate for {ticker} is greater than or equal to WACC. Adjusting growth rate to WACC.")
            terminal_growth = WACC - 0.01

        terminal_value = (forecasted_cash_flows[-1] * (1 + terminal_growth)) / (WACC - terminal_growth)

        if terminal_value < 0:
            terminal_value = 0
            print(f"Terminal value for {ticker} is negative. Setting to 0.")

        present_value_cash_flows = [cf / (1 + WACC)**(i + 1) for i, cf in enumerate(forecasted_cash_flows)]
        present_value_terminal_value = terminal_value / (1 + WACC)**years

        intrinsic_value = sum(present_value_cash_flows) + present_value_terminal_value
        intrinsic_value_per_share = intrinsic_value / shares_outstanding

        print(f"Intrinsic Value per Share for {ticker}: {intrinsic_value_per_share}")

        return intrinsic_value_per_share, forecasted_cash_flows, terminal_value
    except Exception as e:
        logging.error(f"Error calculating DCF for {ticker}: {e}")
        return None, None, None

def evaluate(ticker, intrinsic_value_per_share):
    try:
        print(f"Evaluating {ticker}...")
        current_shareprice = yf.Ticker(ticker).info.get('previousClose', None)
        if current_shareprice is None:
            print(f"Current share price not available for {ticker}.")
            return None

        intrinsic_value_per_share = float(intrinsic_value_per_share)
        current_shareprice = float(current_shareprice)
        if intrinsic_value_per_share > current_shareprice:
            return f"Potential upside for {ticker}: ${(intrinsic_value_per_share - current_shareprice):.2f}"
        else:
            return f"Potential downside for {ticker}: ${(current_shareprice - intrinsic_value_per_share):.2f}"
    except ValueError as e:
        logging.error(f"Error comparing values for {ticker}: {e}")
        return None

def main():
    ticker = get_ticker()
    cashflow_statement, historical_cash_flows, shares_outstanding = parse(ticker)
    
    if cashflow_statement is None or historical_cash_flows is None or shares_outstanding is None:
        return

    WACC = calculate_wacc(ticker, shares_outstanding)
    
    if WACC is None:
        return

    cashflow_growth, terminal_growth = get_growth()
    
    if cashflow_growth is None or terminal_growth is None:
        return

    intrinsic_value_per_share, forecasted_cash_flows, terminal_value = dcf(ticker, WACC, historical_cash_flows, shares_outstanding, terminal_growth, cashflow_growth)
    
    if intrinsic_value_per_share is None:
        return

    evaluation = evaluate(ticker, intrinsic_value_per_share)
    if evaluation:
        print(evaluation)

if __name__ == "__main__":
    main()
