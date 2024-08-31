---------------------------
SP500_Filter.py 
---------------------------
This application allows users to input their preferred weights for various financial ratios, specifying whether they want each ratio to be maximized or minimized. It then retrieves an up-to-date list of S&P 500 index companies and scrapes the necessary data for each ticker. Each company is individually ranked based on each metric, and using the user-defined weights, the app calculates a composite score to rank the companies from best to worst. Users can also download the data in Excel format for further analysis. This app provides a quick overview of S&P 500 companies, serving as a starting point for identifying potentially undervalued or overvalued stocks for more detailed examination.

More Updates I need to consider
1)The App might take a bit to load when opening --> need to work on efficiencies in the code
2)Potentially add other index's
3)Add more ratios

---------------------------
AAPL_DCF.py
---------------------------
This Python script performs a simple discounted cashflow model for Apple by extracting and processing data from Yahoo Finance and FRED. It calculates key metrics such as beta, cost of equity, and the Weighted Average Cost of Capital (WACC). 
The script then estimates future revenue growth rates and projects financial figures including revenue, EBIT, and capital expenditures. 
It calculates free cash flows, terminal value, and discounts these to determine the enterprise value of the company. 
The intrinsic value per share is compared to the current stock price to assess potential upside or downside. 
The results, including detailed projections and valuations, are exported to an Excel file for further analysis.

---------------------------
AAPL_DCF.py
---------------------------
