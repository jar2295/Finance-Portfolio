import math
import yfinance as yf
import pandas as pd
import pandas_datareader as pdr
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import json
from fredapi import Fred
import tkinter as tk
from bs4 import BeautifulSoup
import requests
import openpyxl
import xlsxwriter
import os

# Display all rows
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', '{:.2f}'.format)

# Global variables
ticker_input = "aapl"
years = 5
end_date = dt.datetime.now()
start_date = end_date - dt.timedelta(days=365 * 10)
tax_rate = 0.29

def retrieve_data( ticker_input):
    # Create the yfinance Ticker object
    ticker = yf.Ticker(ticker_input) 
    balance_sheet = ticker.balancesheet.iloc[:, 0:4].iloc[:, ::-1]
    income_statement = ticker.financials.iloc[:, 0:4].iloc[:, ::-1]
    cash_flow_statement = ticker.cashflow.iloc[:, 0:4].iloc[:, ::-1]
    info = ticker.info
    
    historical_data = yf.download(ticker_input, start=start_date, end=end_date)
    sp500_data = yf.download('^GSPC', start=start_date, end=end_date)

    #turn raw data into dataframe.
    df_balance_sheet = pd.DataFrame(balance_sheet)
    df_income_statement = pd.DataFrame(income_statement)
    df_cash_flow_statement = pd.DataFrame(cash_flow_statement)

    return ticker, df_balance_sheet, df_income_statement, df_cash_flow_statement, historical_data, sp500_data, income_statement, info

def metric_calculations(df_balance_sheet, df_income_statement, df_cash_flow_statement, historical_data, sp500_data, ticker):
# Extract adjusted closing prices
    stock_adj_close = historical_data['Adj Close']
    index_adj_close = sp500_data['Adj Close']

    # Reverse the data order to go from newest to oldest
    stock_adj_close = stock_adj_close
    index_adj_close = index_adj_close

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
    beta_calculated = beta

    beta1 = ticker.info.get("beta", None)

# Calculate Cost of Equity
    # Risk-Free Rate
    fred = Fred(api_key='4978884d3d995014011229a1d6b98f1b')
    ten_year_treasury_rate = fred.get_series_latest_release('GS10') / 100
    risk_free_rate = ten_year_treasury_rate.iloc[-1]

    # Calculate cumulative return over the period
    trading_days_per_year = 252
    cumulative_return_sp500 = (index_adj_close.iloc[-1] / index_adj_close.iloc[0]) - 1
    avg_annual_return_sp500 = (1 + cumulative_return_sp500) ** (1 / (len(index_adj_close) / trading_days_per_year)) - 1

    # Calculate market risk premium (annualized)
    risk_premium = avg_annual_return_sp500 - risk_free_rate 

# CAPM
    cost_of_equity = risk_free_rate + beta * risk_premium

# Weighted Average Cost of Capital (WACC)
    # Total value of equity
    current_ticker_price = stock_adj_close.iloc[-1]
    shares_outstanding_label = "Share Issued"
    shares_outstanding = df_balance_sheet.loc[shares_outstanding_label].values[0]
    market_value_of_equity = current_ticker_price * shares_outstanding

    # Total Value of Debt
    total_debt = df_balance_sheet.loc['Total Debt'].values[0]
    market_value_of_debt = total_debt

    # Market value of the Firm
    total_market_value = market_value_of_equity + market_value_of_debt

    # Capital structure
    weight_of_equity = market_value_of_equity / total_market_value
    weight_of_debt = market_value_of_debt / total_market_value
    after_tax_cost_of_debt = (df_income_statement.loc['Interest Expense'].values[0] / total_debt) * (1 - tax_rate)
    WACC = (weight_of_equity * cost_of_equity) + (weight_of_debt * after_tax_cost_of_debt)


    return beta1, beta_calculated, beta, risk_free_rate, risk_premium, cost_of_equity, market_value_of_debt, market_value_of_equity, WACC, weight_of_debt, weight_of_equity, after_tax_cost_of_debt

def revenue_growth_rate(income_statement):
    
    #collect revenue data
    revenue = income_statement.loc['Total Revenue']
    revenue_series = pd.Series(revenue.values, index=income_statement.columns)

    #historical rev growth
    yoy_rev_growth = revenue_series.pct_change().dropna()
    average_yoy_growth = yoy_rev_growth.mean()
    ending_value = revenue_series.iloc[-1]
    starting_value = revenue_series.iloc[0]
    num_years = len(revenue_series) - 1

    #multiple methods of calculating growth rate.
    CAGR = ((ending_value / starting_value) ** (1 / num_years)) - 1
    rolling_growth_rate = revenue_series.pct_change().rolling(window=3).mean().dropna()
    geometric_mean_growth_rate = (np.prod(1 + yoy_rev_growth)) ** (1 / len(yoy_rev_growth)) - 1
    #average of the revenue growth rates
    growth = (CAGR + average_yoy_growth + rolling_growth_rate.mean() + geometric_mean_growth_rate) / 4

    return growth, ending_value, revenue_series

def projected_figures(df_income_statement, income_statement, growth, ticker):
    #retrieve figures
    most_recent_revenue = df_income_statement.loc['Total Revenue'].iloc[-1]
    revenue = df_income_statement.loc['Total Revenue']
    ebit = df_income_statement.loc['EBIT']
    
    def project_revenue():
    #project revenue with calculated growth rate
        projected_revenues = []
        for year in range(1, years + 1):
            future_revenue = most_recent_revenue * ((1 + growth) ** year)
            projected_revenues.append(future_revenue)
        future_years = pd.date_range(start=pd.to_datetime(income_statement.columns[-1]), periods=years+1, freq='Y')[1:]
        projected_revenue_series = pd.Series(projected_revenues, index=future_years, name='Projected Revenue')
        return projected_revenue_series, future_years
    projected_revenue_series, future_years = project_revenue()

    def project_ebit():
        #method 1 using average histroical ebit ratio
        ebit_ratio = ebit / revenue
        average_ebit_ratio = ebit_ratio.mean()
        projected_ebit1 =  projected_revenue_series * average_ebit_ratio

        #method 2 using average ebit growth rate from histroical data.
        ebit_series = pd.Series(ebit.values, index=income_statement.columns)
        ebit_growth_rate= ebit_series.pct_change().dropna()
        ebit_growth_rate= ebit_growth_rate.mean()

        projected_ebit2 = []
        most_recent_ebit = ebit.iloc[-1]
        for year in range(1, years + 1):
            future_ebit = most_recent_ebit * ((1 + ebit_growth_rate) ** year)
            projected_ebit2.append(future_ebit)
        projected_ebit2 = pd.Series(projected_ebit2, index=future_years, name='Projected EBIT')

        #average the two methods
        projected_ebit = pd.Series(((projected_ebit1 + projected_ebit2)/2), name='Projected Ebit')
        return projected_ebit
    projected_ebit = project_ebit()

    def project_NWC():
        # Retrieve balance sheet and financials data
        balance_sheet = ticker.balancesheet
        financials = ticker.financials

        # Check available labels
        available_labels = balance_sheet.index
    
        # Historical data
        current_assets = balance_sheet.loc["Current Assets"]
        current_liabilities = balance_sheet.loc["Current Liabilities"]
        cost_of_revenue = financials.loc["Cost Of Revenue"]
        revenue = financials.loc["Total Revenue"]

        if cost_of_revenue.empty or revenue.empty:
            raise ValueError("Cost Of Revenue or Total Revenue data is missing.")

        cogs_margin = cost_of_revenue / revenue
        av_cogs_margin = cogs_margin.mean()

        # Project future NWC
        projected_cogs = projected_revenue_series * av_cogs_margin

        # Accounts Receivable (AR) Days
        AR = balance_sheet.loc["Receivables"].dropna()
        AR_Days = (AR / revenue) * 365
        AR_av_days = AR_Days.mean()
        projected_ar = (projected_revenue_series * AR_av_days) / 365

        # Inventory Days
        inventory = balance_sheet.loc["Inventory"].dropna()
        inventory_days = (inventory / cost_of_revenue) * 365
        av_inv_days = inventory_days.mean()
        projected_inventory = (projected_cogs * av_inv_days) / 365        

        # Accounts Payable (AP) Days
        AP = balance_sheet.loc["Accounts Payable"].dropna()
        AP_days = (AP / cost_of_revenue) * 365
        av_AP_days = AP_days.mean()
        projected_AP = (projected_cogs * av_AP_days) / 365

        # Other Current Assets (OCA)

        OCA = balance_sheet.loc["Other Current Assets"].dropna().iloc[::-1] if "Other Current Assets" in available_labels else pd.Series()
        most_recent_oca = OCA.iloc[-1] if not OCA.empty else 0
        projected_OCA = [most_recent_oca * ((1 + growth) ** year) for year in range(1, years + 1)]
        future_years = pd.date_range(start=pd.to_datetime(f"{OCA.index[-1].year + 1}-01-01"), periods=years, freq='Y')
        projected_OCA = pd.Series(projected_OCA, index=future_years, name='Projected OCA')      

        # Other Current Liabilities (OCL)
        OCL = balance_sheet.loc["Other Current Liabilities"].dropna().iloc[::-1] if "Other Current Liabilities" in available_labels else pd.Series()
        most_recent_ocl = OCL.iloc[-1] if not OCL.empty else 0
        projected_OCL = [most_recent_ocl * ((1 + growth) ** year) for year in range(1, years + 1)]
        projected_OCL = pd.Series(projected_OCL, index=future_years, name='Projected OCL')      

        # Short-term investments
        short_term_investments_label = "Other Short Term Investments"
        projected_short_term_investments = balance_sheet.loc[short_term_investments_label].mean() if short_term_investments_label in available_labels else 0
        projected_short_term_investments = pd.Series([projected_short_term_investments / 5] * years, index=future_years, name='Projected Short Term Investments')    

        #project short term debt 
        # Find a suitable label for short-term debt
        if "Commercial Paper" in balance_sheet.index and "Other Current Borrowings" in balance_sheet.index:
            Projected_short_term_debt = (balance_sheet.loc["Commercial Paper"] + balance_sheet.loc["Other Current Borrowings"]).mean()
        elif "Short Term Debt" in balance_sheet.index:
            Projected_short_term_debt = balance_sheet.loc["Short Term Debt"].mean()
        else:
            Projected_short_term_debt = 0  # Handle cases where no appropriate label is available

        Projected_short_term_debt = pd.Series([Projected_short_term_debt / 5] * years, index=future_years, name='Projected Short Term Debt')    

        # Projected Short Term Debt
        current_debt = balance_sheet.loc["Current Debt"].dropna().iloc[::-1] if "Current Debt" in available_labels else pd.Series()
        current_debt_growth = current_debt.pct_change().mean() if not current_debt.empty else 0
        most_recent_current_debt = current_debt.iloc[-1] if not current_debt.empty else 0
        projected_current_debt = [most_recent_current_debt * ((1 + current_debt_growth) ** year) for year in range(1, years + 1)]
        projected_current_debt = pd.Series(projected_current_debt, index=future_years, name='Projected Current Debt')


        # Calculate projected Current Liabilities
        Projected_Current_Liabilities = projected_AP + projected_current_debt + projected_OCL+ Projected_short_term_debt

        # Projected Cash
        cash = balance_sheet.loc["Cash And Cash Equivalents"].dropna().iloc[::-1]
        cash_ratio = cash / current_liabilities 
        av_cash_ratio = cash_ratio.mean()
        projected_cash = Projected_Current_Liabilities * av_cash_ratio

        # Calculate projected Current Assets
        Projected_Current_Assets = projected_ar + projected_inventory + projected_cash + projected_OCA + projected_short_term_investments

        # NWC
        historical_nwc = current_assets.dropna() - current_liabilities.dropna()
        historical_nwc_series = pd.Series(historical_nwc.values, index=historical_nwc.index)

        # Future years range
        projected_nwc = Projected_Current_Assets - Projected_Current_Liabilities
        projected_nwc_series = pd.Series(projected_nwc.values, index=future_years, name='Projected NWC')

        # Combine historical and projected NWC in the correct order
        combined_nwc = pd.concat([historical_nwc_series, projected_nwc_series])
        combined_nwc = combined_nwc.sort_index()  # Ensure chronological order

        # Calculate the change in NWC
        projected_change_in_nwc = combined_nwc.diff().dropna()
        projected_change_in_nwc = projected_change_in_nwc.loc[projected_change_in_nwc.index >= future_years[0]]

        return projected_cogs, combined_nwc,historical_nwc, AR_Days, AR_av_days, projected_revenue_series, projected_change_in_nwc, Projected_Current_Assets, Projected_Current_Liabilities, projected_ar, projected_inventory, projected_OCA, projected_cash, projected_AP, projected_current_debt, projected_OCL
    projected_cogs, combined_nwc, historical_nwc,AR_Days, AR_av_days, projected_revenue_series, projected_change_in_nwc, Projected_Current_Assets, Projected_Current_Liabilities, projected_ar, projected_inventory, projected_OCA, projected_cash, projected_AP, projected_current_debt, projected_OCL,  = project_NWC()

    def project_capex():
        #capex projections 
        capex = ticker.cashflow.loc["Capital Expenditure"].dropna().iloc[::-1]
        capex_percentage_rev = capex/revenue
        av_capex_percentage_rev = capex_percentage_rev.mean()

        projected_capex = projected_revenue_series * av_capex_percentage_rev


        return projected_capex
    projected_capex = project_capex()

    def project_depreciation():
        # Assuming you have already retrieved the Depreciation data
        depreciation = ticker.cashflow.loc["Depreciation And Amortization"].dropna().iloc[::-1]

        # Calculate the average historical depreciation
        average_depreciation = depreciation.mean()

        # Project depreciation for the next 5 years
        projected_depreciation = [average_depreciation] * 5

        # Create a DataFrame for better visualization
        future_years = pd.date_range(start=pd.to_datetime(f"{depreciation.index[-1].year + 1}-01-01"), periods=5, freq='Y')
        projected_depreciation_df = pd.DataFrame(data=projected_depreciation, index=future_years, columns=['Depreciation'])


        return projected_depreciation_df
    projected_depreciation_df = project_depreciation()


    return projected_cogs, combined_nwc,historical_nwc, AR_Days, AR_av_days, projected_revenue_series, projected_ebit, projected_change_in_nwc, projected_capex, projected_depreciation_df, Projected_Current_Assets, Projected_Current_Liabilities, projected_ar, projected_inventory, projected_OCA, projected_cash, projected_AP, projected_current_debt, projected_OCL

def calculate_fcff(projected_ebit, projected_change_in_nwc, projected_capex, projected_depreciation_df):
    # Ensure all inputs are pandas Series/DataFrames with numeric data
    if isinstance(projected_ebit, (pd.Series, pd.DataFrame)) and \
       isinstance(projected_change_in_nwc, (pd.Series, pd.DataFrame)) and \
       isinstance(projected_capex, (pd.Series, pd.DataFrame)) and \
       isinstance(projected_depreciation_df, (pd.Series, pd.DataFrame)):

        taxes = projected_ebit * tax_rate
        nopat = projected_ebit - taxes

        # Ensure correct arithmetic with Series/DataFrames
        projected_fcff = nopat + projected_depreciation_df['Depreciation'] - projected_capex - projected_change_in_nwc

        return projected_fcff, nopat
    else:
        raise ValueError("All inputs must be pandas Series or DataFrames containing numeric data.")

def calculate_terminal_value(projected_fcff, WACC, ticker):
    #terminal growth rate
    free_cash_flow = ticker.cash_flow.loc["Free Cash Flow"].dropna()
    first_cash_flow = free_cash_flow.iloc[3]
    last_cash_flow = free_cash_flow.iloc[0]

    terminal_growth = ((last_cash_flow/first_cash_flow)**(1/4))-1

    last_fcff = projected_fcff.iloc[-1]
 
    terminal_value = (last_fcff * (1 + terminal_growth))/(WACC - terminal_growth)

    return last_fcff, terminal_value, free_cash_flow, first_cash_flow, last_cash_flow, terminal_growth

def discount(projected_fcff, terminal_value, growth, WACC):
    # Number of periods (length of FCFF list)
    n = len(projected_fcff)

    #Calculate discounted FCFFs
    discounted_fcffs = [fcff / (1 + WACC)**(t + 1) for t, fcff in enumerate(projected_fcff)]

    # Discount the terminal value
    discounted_terminal_value = terminal_value / (1 + WACC)**n

    # Sum of discounted FCFFs and discounted terminal value
    enterprise_value = sum(discounted_fcffs) + discounted_terminal_value
    return enterprise_value

def value(enterprise_value, ticker, info):
    shares_outstanding = info.get('sharesOutstanding', 'Data not available')
    intrinsic_price = enterprise_value / shares_outstanding

    #upside//downside potential

    price_data = ticker.history()
    current_price = price_data['Close'].iloc[-1]

    variance = intrinsic_price - current_price
    variance = intrinsic_price - current_price

    if variance > 0:
        print(f"Potential Upside: ${variance}, per share")
    else:
        print(f"Potential Downside: ${variance}, per share")

    return intrinsic_price



def debug_data(data, name):
    print(f"--- {name} ---")
    if isinstance(data, pd.Series):
        print(data.head())
    elif isinstance(data, pd.DataFrame):
        print(data.head())
    else:
        print("Unknown type")
    print("--------------------")

def extract_values(series):
    """Extracts numeric values from a pandas Series."""
    return series.apply(lambda x: x if isinstance(x, (int, float)) else float(x.split()[0]))



def export_to_excel(ticker_input, projected_revenue_series, projected_ebit, projected_change_in_nwc, projected_cogs, combined_nwc, projected_capex, projected_depreciation_df, Projected_Current_Assets, Projected_Current_Liabilities, projected_ar, projected_inventory, projected_OCA, projected_cash, projected_AP, projected_current_debt, projected_OCL):
    try:
        # Debug each dataset before combining
        debug_data(projected_revenue_series, 'Projected Revenue Series')
        debug_data(projected_ebit, 'Projected EBIT')
        debug_data(projected_change_in_nwc, 'Projected Change in NWC')
        debug_data(projected_cogs, 'Projected COGS')
        debug_data(combined_nwc, 'Combined NWC')
        debug_data(projected_capex, 'Projected CAPEX')
        debug_data(projected_depreciation_df, 'Projected Depreciation')
        debug_data(Projected_Current_Assets, 'Projected Current Assets')
        debug_data(Projected_Current_Liabilities, 'Projected Current Liabilities')
        debug_data(projected_ar, 'Projected Accounts Receivable')
        debug_data(projected_inventory, 'Projected Inventory')
        debug_data(projected_OCA, 'Projected Other Current Assets')
        debug_data(projected_cash, 'Projected Cash')
        debug_data(projected_AP, 'Projected Accounts Payable')
        debug_data(projected_current_debt, 'Projected Current Debt')
        debug_data(projected_OCL, 'Projected Other Current Liabilities')

        # Extract numeric values from series
        # ... (code omitted for brevity) ...

        # Combine all the data into a single DataFrame
        combined_data = pd.DataFrame({
            'Metric': [
                'Revenue', 'EBIT', 'Change in NWC', 'COGS', 'NWC', 'CAPEX', 'Depreciation',
                'Current Assets', 'Current Liabilities', 'Accounts Receivable', 'Inventory',
                'Other Current Assets', 'Cash', 'Accounts Payable', 'Current Debt', 'Other Current Liabilities'
            ]
        })

        # Define the years to be included
        years = ['2024', '2025', '2026', '2027']  # Adjust as needed

        # Populate the DataFrame with data for each year
        for year in years:
            combined_data[year] = [
                projected_revenue_series.get(year, 'N/A'),
                projected_ebit.get(year, 'N/A'),
                projected_change_in_nwc.get(year, 'N/A'),
                projected_cogs.get(year, 'N/A'),
                combined_nwc.get(year, 'N/A'),
                projected_capex.get(year, 'N/A'),
                projected_depreciation_df.get(year, 'N/A'),
                Projected_Current_Assets.get(year, 'N/A'),
                Projected_Current_Liabilities.get(year, 'N/A'),
                projected_ar.get(year, 'N/A'),
                projected_inventory.get(year, 'N/A'),
                projected_OCA.get(year, 'N/A'),
                projected_cash.get(year, 'N/A'),
                projected_AP.get(year, 'N/A'),
                projected_current_debt.get(year, 'N/A'),
                projected_OCL.get(year, 'N/A')
            ]

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Define the path for the output file
        output_file_path = os.path.join(script_dir, f'{ticker_input}_output.xlsx')

        # Create an ExcelWriter object using XlsxWriter
        with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
            # Write the combined DataFrame to a single sheet
            combined_data.to_excel(writer, sheet_name='Financials', index=False)

            # Access the workbook and sheet objects for formatting
            workbook = writer.book
            worksheet = writer.sheets['Financials']

            # Formatting for the 'Financials' sheet
            worksheet.set_column('A:A', 30)  # Adjust column width for metrics
            worksheet.set_column('B:Z', 15)  # Adjust column width for years

        print(f"Data exported successfully to {output_file_path}")

    except ValueError as ve:
        print(f"ValueError: {ve}")
    except Exception as e:
        print(f"Error exporting to Excel: {e}")



def main():
    try:
        # Example of how retrieve_data, metric_calculations, revenue_growth_rate, and projected_figures might be used

        ticker, df_balance_sheet, df_income_statement, df_cash_flow_statement, historical_data, sp500_data, income_statement, info = retrieve_data(ticker_input)
        beta1, beta_calculated, beta, risk_free_rate, risk_premium, cost_of_equity, market_value_of_debt, market_value_of_equity, WACC, weight_of_debt, weight_of_equity, after_tax_cost_of_debt = metric_calculations(df_balance_sheet, df_income_statement, df_cash_flow_statement, historical_data, sp500_data, ticker)
        growth, ending_value, revenue_series = revenue_growth_rate(income_statement)
        projected_cogs, combined_nwc, historical_nwc, AR_Days, AR_av_days, projected_revenue_series, projected_ebit, projected_change_in_nwc, projected_capex, projected_depreciation_df, Projected_Current_Assets, Projected_Current_Liabilities, projected_ar, projected_inventory, projected_OCA, projected_cash, projected_AP, projected_current_debt, projected_OCL = projected_figures(df_income_statement, income_statement, growth, ticker)

        projected_fcff, nopat = calculate_fcff(projected_ebit, projected_change_in_nwc, projected_capex, projected_depreciation_df)
        last_fcff, terminal_value, free_cash_flow, first_cash_flow, last_cash_flow, terminal_growth = calculate_terminal_value(projected_fcff, WACC, ticker)
        enterprise_value = discount(projected_fcff, terminal_value, growth, WACC)
        intrinsic_price = value(enterprise_value, ticker, info)

        export_to_excel(ticker_input, projected_revenue_series, projected_ebit, projected_change_in_nwc, projected_cogs, combined_nwc, projected_capex, projected_depreciation_df, Projected_Current_Assets, Projected_Current_Liabilities, projected_ar, projected_inventory, projected_OCA, projected_cash, projected_AP, projected_current_debt, projected_OCL)

        print("Financial analysis and projections completed successfully!")
        print(f"Beta: {beta}")
        print(f"Cost of Equity: {cost_of_equity}")
        print(f"WACC: {WACC}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
