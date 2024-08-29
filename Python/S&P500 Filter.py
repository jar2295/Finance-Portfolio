import yfinance as yf
import pandas as pd
from lxml import html
import requests
import datetime as dt
import urllib3
from fredapi import Fred
import logging
import time  # Import time for the delay
import os
from openpyxl import load_workbook

# Global variables
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(filename='dcf_analysis.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', '{:.2f}'.format)

years = 5
delay_seconds = 5  # Set delay time between requests


def get_sp500_tickers():
    url = "https://stockanalysis.com/list/sp-500-stocks/"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    # Parse the table using lxml
    tree = html.fromstring(response.content)
    table_rows = tree.xpath('//*[@id="main-table"]/tbody/tr')
    
    # Initialize a list to store each row of data
    data = []
    
    for row in table_rows:
        # Extract text from each cell in the row
        row_data = [cell.text_content().strip() for cell in row.xpath('.//td')]
        data.append(row_data)
    
    # Convert the list of lists into a DataFrame
    sp500_df = pd.DataFrame(data).loc[:,1]

    # For testing, limit to one ticker (e.g., Apple)
    #sp500_df = ["AAPL"]  # You can remove this line after testing
    
    return sp500_df

sp500_df = get_sp500_tickers()


def parse(ticker):
    try:
        print(f"Parsing data for {ticker}...")
        ticker_data = yf.Ticker(ticker) 
        cashflow_statement = ticker_data.cash_flow.iloc[:, 0:4].iloc[:, ::-1]  # Reverse the columns
        historical_cash_flows = cashflow_statement.loc["Free Cash Flow"]

        # Convert the historical cash flows to float (if they are not)
        historical_cash_flows = historical_cash_flows.astype(float)

        yahoo_url = f"https://finance.yahoo.com/quote/{ticker}/analysis?p={ticker}"
        xpath = '//*[@id="nimbus-app"]/section/section/section/article/section[7]/div/table/tbody/tr[5]/td[2]'
        response = requests.get(yahoo_url, headers={'User-Agent': 'Mozilla/5.0'})
        growth = float(html.fromstring(response.content).xpath(xpath)[0].text_content().strip().replace('%', '')) / 100

        shares_outstanding = ticker_data.info.get("sharesOutstanding")
        
        print(f"Ticker: {ticker}, Free Cash Flows: {historical_cash_flows}, Growth Rate: {growth}, Shares Outstanding: {shares_outstanding}")

        return historical_cash_flows.iloc[-1], historical_cash_flows, growth, shares_outstanding, historical_cash_flows.iloc[0] if not historical_cash_flows.empty else None

    except Exception as e:
        logging.error(f"Error parsing data for {ticker}: {e}")
        return None, None, None, None, None


def calculate_wacc(ticker, shares_outstanding):
    try:
        print(f"Calculating WACC for {ticker}...")  # Debugging statement
        balance_sheet = yf.Ticker(ticker).balancesheet.iloc[:, 0:4].iloc[:, ::-1]
        income_statement = yf.Ticker(ticker).financials.iloc[:, 0:4].iloc[:, ::-1]
        cash_flow_statement = yf.Ticker(ticker).cashflow.iloc[:, 0:4].iloc[:, ::-1]

        end_date = dt.datetime.now()
        start_date = end_date - dt.timedelta(days=365 * 10)
        historical_data = yf.download(ticker, start=start_date, end=end_date)
        sp500_data = yf.download('^GSPC', start=start_date, end=end_date)

        # Extract adjusted closing prices
        stock_adj_close = historical_data['Adj Close']
        index_adj_close = sp500_data['Adj Close']

        # Calculate daily returns
        stock_returns = stock_adj_close.pct_change().dropna()
        index_returns = index_adj_close.pct_change().dropna()

        # Combine returns into a single DataFrame
        combined = pd.concat([stock_returns, index_returns], axis=1).dropna()
        stock_returns = combined.iloc[:, 0]
        index_returns = combined.iloc[:, 1] 

        # Calculate covariance and variance of returns
        covariance = stock_returns.cov(index_returns)
        variance = index_returns.var()

        # Calculate beta
        beta = covariance / variance    

        # Calculate Cost of Equity
        fred = Fred(api_key='4978884d3d995014011229a1d6b98f1b')
        ten_year_treasury_rate = fred.get_series_latest_release('GS10') / 100
        risk_free_rate = ten_year_treasury_rate.iloc[-1]

        trading_days_per_year = 252
        cumulative_return_sp500 = (index_adj_close.iloc[-1] / index_adj_close.iloc[0]) - 1
        avg_annual_return_sp500 = (1 + cumulative_return_sp500) ** (1 / (len(index_adj_close) / trading_days_per_year)) - 1

        risk_premium = avg_annual_return_sp500 - risk_free_rate 
        cost_of_equity = risk_free_rate + beta * risk_premium

        # Weighted Average Cost of Capital (WACC)
        current_ticker_price = stock_adj_close.iloc[-1]
        market_value_of_equity = current_ticker_price * shares_outstanding

        total_debt = balance_sheet.loc['Total Debt'].values[0]
        market_value_of_debt = total_debt

        total_market_value = market_value_of_equity + market_value_of_debt
        weight_of_equity = market_value_of_equity / total_market_value
        weight_of_debt = market_value_of_debt / total_market_value
        after_tax_cost_of_debt = (income_statement.loc['Interest Expense'].values[0] / total_debt) * (1 - 0.2)
        WACC = (weight_of_equity * cost_of_equity) + (weight_of_debt * after_tax_cost_of_debt)

        print(f"WACC for {ticker}: {WACC}")  # Debugging statement

        return WACC
    except Exception as e:
        logging.error(f"Error calculating WACC for {ticker}: {e}")
        return None
def dcf(ticker, WACC, fcf5, historical_cash_flows, shares_outstanding, growth):
    try:
        print(f"Calculating DCF for {ticker}...")
        forecasted_cash_flows = [float(fcf5)]
        for i in range(1, years):
            forecasted_cash_flows.append(forecasted_cash_flows[-1] * (1 + growth))

        # Adjust growth rate if it exceeds WACC
        if growth >= WACC:
            print(f"Growth rate for {ticker} is greater than or equal to WACC. Adjusting growth rate to WACC.")
            growth = WACC - 0.01  # Reduce growth slightly to avoid division by zero

        terminal_value = (forecasted_cash_flows[-1] * (1 + growth)) / (WACC - growth)
        
        # Ensure terminal value is not negative
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
        return None, []

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

def run(sp500_df):
    results = []

    # Limit to the first 10 tickers
    sp500_df = sp500_df.head(10)

    for ticker in sp500_df:
        print(f"Processing {ticker}...")
        try:
            fcf5, historical_cash_flows, growth, shares_outstanding, _ = parse(ticker)
            if fcf5 and shares_outstanding:
                WACC = calculate_wacc(ticker, shares_outstanding)
                if WACC is None:
                    print(f"Skipping {ticker} due to invalid WACC.")
                    continue
                
                intrinsic_value_per_share, forecasted_cash_flows, terminal_value = dcf(ticker, WACC, fcf5, historical_cash_flows, shares_outstanding, growth)
                if intrinsic_value_per_share is None:
                    print(f"Skipping {ticker} due to invalid intrinsic value.")
                    continue
                
                current_shareprice = yf.Ticker(ticker).info.get('previousClose', None)
                if current_shareprice is None:
                    print(f"Skipping {ticker} due to missing current share price.")
                    continue

                potential_return = evaluate(ticker, intrinsic_value_per_share)
                
                # Extract individual historical cash flows
                historical_fcf_list = historical_cash_flows.tolist()
                historical_fcf_dict = {f"FCF {i+1}": historical_fcf_list[i] for i in range(len(historical_fcf_list))}
                
                # Extract individual forecasted cash flows
                forecasted_fcf_list = forecasted_cash_flows  # This should be a list, not a Series
                forecasted_fcf_dict = {f"FCF {i+5}": forecasted_fcf_list[i] for i in range(len(forecasted_fcf_list))}
                
                results.append({
                    'Ticker': ticker,
                    **historical_fcf_dict,
                    **forecasted_fcf_dict,
                    'WACC': WACC,
                    'Growth Rate': growth,
                    "Terminal Value": terminal_value,
                    "shares outstanding": shares_outstanding,
                    'Intrinsic Value per Share': intrinsic_value_per_share,
                    'Current Share Price': current_shareprice,
                    'Potential Return': potential_return
                })
            else:
                print(f"Skipping {ticker} due to missing data...")

            time.sleep(delay_seconds)

        except Exception as e:
            logging.error(f"Error processing {ticker}: {e}")

    return results


results = run(sp500_df)

def save_results_to_excel(results):
    results_df = pd.DataFrame(results)
    excel_file_path = "/Users/jaredherber/Desktop/Portfolio/sp500.xlsx"
    
    if not results_df.empty:  # Ensure results DataFrame is not empty
        try:
            # Create a new Excel writer object
            if os.path.exists(excel_file_path):
                # If the file exists, append data to a new sheet
                with pd.ExcelWriter(excel_file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    results_df.to_excel(writer, sheet_name='Raw Data', index=False)
                print(f"Results appended to {excel_file_path}")
            else:
                # If the file does not exist, create a new one with the data
                with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
                    results_df.to_excel(writer, sheet_name='Raw Data', index=False)
                print(f"File {excel_file_path} created with new data")
            
            print("Results saved successfully.")
            print(results_df)
        
        except Exception as e:
            print(f"An error occurred while saving the file: {e}")
    else:
        print("No results to display.")

save_results_to_excel(results)
