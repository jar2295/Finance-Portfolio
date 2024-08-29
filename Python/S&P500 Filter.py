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
# Display all rows
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', '{:.2f}'.format)

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

def parse(ticker):
    ticker = yf.Ticker(ticker) 
    current_price = ticker.history()['Close'].iloc[-1]
    eps =  ticker.info.get('forwardEps')
    pe = current_price/eps


    bve = ticker.balance_sheet.loc['Stockholders Equity'].iloc[0]
    market_cap = ticker.info.get("marketCap")
    price_to_book = market_cap / bve
    print(ticker)
    print(f"Price to Earnings: {pe}")
    print()
    print(f"Price to Book: {price_to_book}")
    print()

    return pe, price_to_book,

def main():
    sp500_df = get_sp500_tickers()

    for ticker in sp500_df:
        pe, price_to_book, = parse(ticker)

         
main()



#pegRatio