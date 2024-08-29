import yfinance as yf
import pandas as pd
from lxml import html
import requests
import logging

# Display all rows
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', '{:.2f}'.format)

# Set up logging
logging.basicConfig(filename='pe_pb_ranking.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


#weightings of each ratio

weight_pe = 0.5
weight_pb = 0.5


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

    #For testing, limit to one ticker (e.g., Apple)
    #sp500_df = ["AAPL"]  # You can remove this line after testing
    
    return sp500_df

def parse(ticker):
    try:
        ticker = yf.Ticker(ticker) 
        current_price = ticker.history()['Close'].iloc[-1]
        eps =  ticker.info.get('forwardEps')
        pe = current_price/eps


        bve = ticker.balance_sheet.loc['Stockholders Equity'].iloc[0]
        market_cap = ticker.info.get("marketCap")
        price_to_book = market_cap / bve
        print(ticker)
        print(f"Price to Earnings: {pe}")
        print(f"Price to Book: {price_to_book}")
        print()

        return pe, price_to_book,

    except Exception as e:
            print(f"Error processing {ticker}: {e}")
            return None, None

def main():
    sp500_df = get_sp500_tickers()

    results = []

    # Limit the list to the first 10 tickers for testing
    sp500_df = sp500_df.head(10)

    for ticker in sp500_df:
        pe, price_to_book = parse(ticker)
        if pe is not None and price_to_book is not None:
            results.append({"Ticker": ticker, "P/E Ratio": pe, "P/B Ratio": price_to_book})

    # Convert results to a DataFrame
    results_df = pd.DataFrame(results)
    
    # Rank by P/E and P/B ratios
    results_df['P/E Rank'] = results_df['P/E Ratio'].rank(ascending=False)
    results_df['P/B Rank'] = results_df['P/B Ratio'].rank(ascending=False)

    #Composite Score
    results_df['Composite Score'] = (results_df['P/E Rank'] * weight_pe) + (results_df['P/B Rank'] * weight_pb)
          
    # Log the rankings
    logging.info("\nP/E and P/B Rankings:\n")
    logging.info(results_df.to_string(index=False))


    # Display the rankings in the console
    print(results_df.sort_values('P/E Rank').to_string(index=False))
    print("\n")
    print(results_df.sort_values('P/B Rank').to_string(index=False))
    print("\nComposite Scores:")
    print(results_df.sort_values('Composite Score').to_string(index=False))


    # Display best and worst scores
    best_score = results_df.loc[results_df['Composite Score'].idxmin()]
    worst_score = results_df.loc[results_df['Composite Score'].idxmax()]

    print("\nBest Composite Score:")
    print(best_score.to_frame().T.to_string(index=False))
    
    print("\nWorst Composite Score:")
    print(worst_score.to_frame().T.to_string(index=False))

main()



#pegRatio

#need to fix whther a high pe is a high or low score and for pb as well
