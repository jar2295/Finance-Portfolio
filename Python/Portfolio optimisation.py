import math
import yfinance as yf
import pandas as pd
import pandas_datareader as pdr
import datetime as dt
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import fredapi as Fred
import scipy


end_date = dt.datetime.now()
start_date = end_date - dt.timedelta(days = 365*5)

stocks = ['NVDA', 'AMD', 'INTC', 'TSLA', 'AAPL', 'MSFT']

adj_close = pd.DataFrame()

for ticker in stocks:
    data = yf.download(ticker, start = start_date, end = end_date)
    adj_close[ticker] = data["Adj Close"]
    print(adj_close.head()) 

#daily returns
print("lognormal Returns")
log_returns = np.log(adj_close/adj_close.shift(1))
print(log_returns.head())

#cumlative returns
print("Cumulative returns")
cumulative_returns = log_returns.cumsum()
print(cumulative_returns.head())

#Cov Matrix (its multiplied by 252 becasue we have been looking at daily returns and want to annualise it)
print("Covariance matrix")
cov_matrix = log_returns.cov()*252
print(cov_matrix)

#standard deviation (.t makes it transposed)
def standard_deviation (weights, cov_matrix):
    variance = weights.T @ cov_matrix @ weights
    return np.sqrt(variance)

#expected returns (annualised)
def expected_return (weights, log_returns):
    return np.sum(log_returns.mean() * weights)* 252

#Fred API
from fredapi import Fred
fred = Fred(api_key='4978884d3d995014011229a1d6b98f1b')
ten_year_treasury_rate = fred.get_series_latest_release('GS10') / 100

#riskfree rate
risk_free_rate = ten_year_treasury_rate.iloc[-1]
print(f"The risk free rate is is {risk_free_rate*100:.2f}%")


#shape ratio
def sharpe_ratio (weights, log_returns, cov_matrix, risk_free_rate):
    return(expected_return (weights, log_returns) - risk_free_rate) / standard_deviation (weights, cov_matrix)

#define the function to minimise (negaitve sharpe ratio)

def neg_sharpe_ratio(weights, log_returns, cov_matrix, risk_free_rate):
    return -sharpe_ratio(weights, log_returns, cov_matrix, risk_free_rate)

#bound of 0 means cant go short and o.5 means no one security can be 50% of the portfolio
constraints = {'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1}
bounds = [(0, 0.5) for _ in range(len(stocks))]

initial_weights = np.array([1/len(stocks)]*len(stocks))

#optimise the weights to maximise the sharpe ratio.
#SLSQP stands for sequential least squares quadratic programing
from scipy.optimize import minimize
optimised_results = minimize(neg_sharpe_ratio, initial_weights, args=(log_returns, cov_matrix, risk_free_rate), method='SLSQP', constraints=constraints, bounds=bounds)

#get optimal weights
optimal_weights = optimised_results.x

print()

#display analytics
print("optimal weights")
for ticker, weight in zip(stocks, optimal_weights):
    print(f"{ticker}: {weight:.4f}")

print()

optimal_portfolio_return = expected_return(optimal_weights, log_returns)
optimal_portfolio_volatility = standard_deviation(optimal_weights, cov_matrix )
optimal_portfolio_ratio = sharpe_ratio(optimal_weights, log_returns, cov_matrix, risk_free_rate)

print(f"Expecte Annual Return: {optimal_portfolio_return:.4f}")
print(f"Expecte volatility: {optimal_portfolio_volatility:.4f}")
print(f"Sharpe Ratio of new portfolio: {optimal_portfolio_ratio:.4f}")

#display portfolio on a plot



plt.figure(figsize=(10,6))
plt.bar(stocks, optimal_weights)

plt.xlabel("Assets")
plt.ylabel("Optimal Weights")
plt.title("Optimal Portfolio Weights")

plt.show()
