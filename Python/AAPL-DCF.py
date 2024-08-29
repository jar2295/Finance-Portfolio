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
from sklearn.linear_model import LinearRegression
# Display all rows
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', '{:.2f}'.format)

# Global variables
ticker_input = "aapl"
ticker = yf.Ticker(ticker_input) 
pd.set_option('display.max_rows', None)
years = 5
end_date = dt.datetime.now()
start_date = end_date - dt.timedelta(days=365 * 10)
tax_rate = 0.29

def retrieve_data(ticker, ticker_input):
    # Create the yfinance Ticker object

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

    return df_balance_sheet, df_income_statement, df_cash_flow_statement, historical_data, sp500_data, income_statement, info
df_balance_sheet, df_income_statement, df_cash_flow_statement, historical_data, sp500_data, income_statement, info = retrieve_data(ticker, ticker_input)

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
beta1, beta_calculated, beta, risk_free_rate, risk_premium, cost_of_equity, market_value_of_debt, market_value_of_equity, WACC, weight_of_debt, weight_of_equity, after_tax_cost_of_debt = metric_calculations(df_balance_sheet, df_income_statement, df_cash_flow_statement, historical_data, sp500_data, ticker)

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
growth, ending_value, revenue_series = revenue_growth_rate(income_statement)

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
        projected_ebit2 = pd.Series(projected_ebit2, index=future_years, name='Projected Revenue')

        #average the two methods
        projected_ebit = (projected_ebit1 + projected_ebit2)/2
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
projected_cogs, combined_nwc, historical_nwc, AR_Days, AR_av_days, projected_revenue_series, projected_ebit, projected_change_in_nwc, projected_capex, projected_depreciation_df, Projected_Current_Assets, Projected_Current_Liabilities, projected_ar, projected_inventory, projected_OCA, projected_cash, projected_AP, projected_current_debt, projected_OCL = projected_figures(df_income_statement, income_statement, growth, ticker)

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
projected_fcff, nopat = calculate_fcff(projected_ebit, projected_change_in_nwc, projected_capex, projected_depreciation_df)

def calculate_terminal_value(projected_fcff, WACC, ticker):
    #terminal growth rate
    free_cash_flow = ticker.cash_flow.loc["Free Cash Flow"].dropna()
    first_cash_flow = free_cash_flow.iloc[3]
    last_cash_flow = free_cash_flow.iloc[0]

    terminal_growth = ((last_cash_flow/first_cash_flow)**(1/4))-1

    last_fcff = projected_fcff.iloc[-1]
 
    terminal_value = (last_fcff * (1 + 0.02))/(WACC - 0.02)

    return last_fcff, terminal_value, free_cash_flow, first_cash_flow, last_cash_flow, terminal_growth
last_fcff, terminal_value, free_cash_flow, first_cash_flow, last_cash_flow, terminal_growth  = calculate_terminal_value(projected_fcff, WACC, ticker)

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
enterprise_value = discount(projected_fcff, terminal_value, growth, WACC)

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
intrinsic_price = value(enterprise_value, ticker, info)


# Print results
print("Base Metrics")
print(f"Ticker: {ticker}")
print(f"Beta: {beta:.4f}")
print(f"Risk Free Rate: {risk_free_rate:.4f}")
print(f"Risk Premium: {risk_premium:.4f}")
print(f"Cost of Equity: {cost_of_equity:.4f}")
print(f"After Tax Cost of Debt: {after_tax_cost_of_debt:.4f}")
print(f"Weight of Debt: {weight_of_debt:.4f}")
print(f"Weight of Equity: {weight_of_equity:.4f}")
print(f"WACC: {WACC:.4f}")


print("revenue")
print(revenue_series)
print(projected_revenue_series)
print("cogs")
print(ticker.financials.loc["Cost Of Revenue"].iloc[::-1])
print(projected_cogs.iloc[::-1])
print("ebit")
print(ticker.financials.loc["EBIT"])
print(projected_ebit)
print()
print("current assets")
print(Projected_Current_Assets)
print("current Liabilities")
print(Projected_Current_Liabilities)
print()
print("NWC")
print(combined_nwc)
print("CAPEX")
print(projected_capex)
print("depreciation")
print(ticker.cash_flow.loc["Depreciation And Amortization"])
print(projected_depreciation_df.iloc[::-1])
print()
print()
print("Free Cash FLow")
print(ticker.cash_flow.loc["Free Cash Flow"])
print(projected_fcff)
print()
print()
print("terminal values")
print(terminal_growth)
print(terminal_value)


view_dep = projected_depreciation_df.squeeze()
view_dep = view_dep.tolist()



