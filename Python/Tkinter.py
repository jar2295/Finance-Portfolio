import tkinter as tk
from tkinter import ttk
import yfinance as yf
import pandas as pd
from lxml import html
import requests
import logging
import time
import threading

class PercentageSlidersApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Percentage Sliders")

        # Variables for sliders and text inputs (whole numbers, no decimals)
        self.slider1_val = tk.IntVar(value=25)
        self.slider2_val = tk.IntVar(value=25)
        self.slider3_val = tk.IntVar(value=25)
        self.slider4_val = tk.IntVar(value=25)

        # Lock to prevent recursive updates
        self.update_lock = False

        # Create sliders and text inputs
        self.create_slider_and_input("P/E Weight", self.slider1_val, 0)
        self.create_slider_and_input("P/B Weight", self.slider2_val, 1)
        self.create_slider_and_input("D/E Weight", self.slider3_val, 2)
        self.create_slider_and_input("PEG Weight", self.slider4_val, 3)

        # Calculate button
        self.calculate_button = ttk.Button(root, text="Calculate", command=self.start_calculation)
        self.calculate_button.grid(row=4, column=0, columnspan=3, pady=10)

        # Output label
        self.output_label = ttk.Label(root, text="Output will be shown here")
        self.output_label.grid(row=6, column=0, columnspan=3, pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, pady=10)

    def create_slider_and_input(self, label, var, row):
        ttk.Label(self.root, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        slider = ttk.Scale(self.root, from_=0, to=100, orient="horizontal", variable=var, command=lambda val, v=var: self.update_sliders(v))
        slider.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        slider.config(length=200)
        input_entry = ttk.Entry(self.root, textvariable=var, width=5)
        input_entry.grid(row=row, column=2, padx=5, pady=5)
        input_entry.bind('<FocusOut>', lambda event, v=var: self.update_entry(event, v))

    def update_sliders(self, changed_var):
        if self.update_lock:
            return
        self.update_lock = True
        values = [self.slider1_val.get(), self.slider2_val.get(), self.slider3_val.get(), self.slider4_val.get()]
        idx = [self.slider1_val, self.slider2_val, self.slider3_val, self.slider4_val].index(changed_var)
        other_indices = [i for i in range(4) if i != idx]
        remaining = 100 - changed_var.get()
        for i in other_indices:
            new_val = max(0, min(remaining, values[i]))
            values[i] = new_val
            remaining -= new_val
        self.slider1_val.set(values[0])
        self.slider2_val.set(values[1])
        self.slider3_val.set(values[2])
        self.slider4_val.set(values[3])
        self.update_lock = False

    def update_entry(self, event, changed_var):
        try:
            value = int(changed_var.get())
            if value < 0:
                changed_var.set(0)
            elif value > 100:
                changed_var.set(100)
            self.update_sliders(changed_var)
        except ValueError:
            self.update_sliders(changed_var)

    def get_sp500_tickers(self):
        url = "https://stockanalysis.com/list/sp-500-stocks/"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        tree = html.fromstring(response.content)
        table_rows = tree.xpath('//*[@id="main-table"]/tbody/tr')
        data = []
        for row in table_rows:
            row_data = [cell.text_content().strip() for cell in row.xpath('.//td')]
            data.append(row_data)
        sp500_df = pd.DataFrame(data).loc[:,1]
        return sp500_df

    def parse(self, ticker, max_retries=3, delay=2):
        attempt = 0
        while attempt < max_retries:
            try:
                ticker_obj = yf.Ticker(ticker)
                history_df = ticker_obj.history(period="1d")

                if history_df.empty:
                    raise ValueError("No data found for ticker")

                current_price = history_df['Close'].iloc[-1]

                eps = ticker_obj.info.get('forwardEps')
                if eps is None:
                    raise ValueError("EPS data is unavailable")

                pe = current_price / eps

                bve = ticker_obj.balance_sheet.loc['Stockholders Equity'].iloc[0]
                market_cap = ticker_obj.info.get("marketCap")
                if bve is None or market_cap is None:
                    raise ValueError("Book value or market cap data is unavailable")

                price_to_book = market_cap / bve

                debt_equity = ticker_obj.info.get("debtToEquity")
                if debt_equity is None:
                    raise ValueError("Debt to Equity data is unavailable")

                peg_ratio = ticker_obj.info.get("pegRatio")
                if peg_ratio is None:
                    raise ValueError("PEG Ratio data is unavailable")

                return pe, price_to_book, debt_equity, peg_ratio

            except ValueError as e:
                logging.error(f"Value error processing {ticker}: {e}")
                return None, None, None, None
            except KeyError as e:
                logging.error(f"Key error processing {ticker}: {e}")
                return None, None, None, None
            except requests.exceptions.RequestException as e:
                logging.error(f"Network error processing {ticker}: {e}")
                time.sleep(delay * 2)  # Increase delay for network errors
            except Exception as e:
                logging.error(f"Unexpected error processing {ticker}: {e}")
                return None, None, None, None
            attempt += 1
            if attempt < max_retries:
                logging.info(f"Retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                logging.error(f"Failed after {max_retries} attempts")
                return None, None, None, None

    def calculate(self):
        results = []
        sp500_df = self.get_sp500_tickers()
        sp500_df = sp500_df 

        self.progress['maximum'] = len(sp500_df)
        self.progress['value'] = 0

        for i, ticker in enumerate(sp500_df):
            pe, price_to_book, debt_equity, peg_ratio = self.parse(ticker)
            if pe is not None and price_to_book is not None and debt_equity is not None and peg_ratio is not None:
                results.append({
                    "Ticker": ticker,
                    "P/E Ratio": pe,
                    "P/B Ratio": price_to_book,
                    "Debt to Equity": debt_equity,
                    "PEG Ratio": peg_ratio
                })
            else:
                logging.info(f"Skipping ticker {ticker} due to data unavailability")

            self.progress['value'] = i + 1
            self.root.update_idletasks()
            time.sleep(1)  # Short delay between requests to avoid rate limits

        if results:
            results_df = pd.DataFrame(results)
            results_df['P/E Rank'] = results_df['P/E Ratio'].rank(ascending=True)
            results_df['P/B Rank'] = results_df['P/B Ratio'].rank(ascending=True)
            results_df['D/E Rank'] = results_df['Debt to Equity'].rank(ascending=True)
            results_df['PEG Rank'] = results_df['PEG Ratio'].rank(ascending=True)

            weight_pe = self.slider1_val.get()
            weight_pb = self.slider2_val.get()
            weight_de = self.slider3_val.get()
            weight_peg = self.slider4_val.get()

            results_df['Composite Score'] = (
                (results_df['P/E Rank'] * weight_pe) +
                (results_df['P/B Rank'] * weight_pb) +
                (results_df['D/E Rank'] * weight_de) +
                (results_df['PEG Rank'] * weight_peg)
            )

            best_score = results_df.loc[results_df['Composite Score'].idxmin()]
            worst_score = results_df.loc[results_df['Composite Score'].idxmax()]

            output_text = f"Best Composite Score:\nTicker: {best_score['Ticker']}\n" \
                        f"P/E Ratio: {best_score['P/E Ratio']:.2f}\n" \
                        f"P/B Ratio: {best_score['P/B Ratio']:.2f}\n" \
                        f"Debt to Equity: {best_score['Debt to Equity']:.2f}\n" \
                        f"PEG Ratio: {best_score['PEG Ratio']:.2f}\n\n" \
                        f"Worst Composite Score:\nTicker: {worst_score['Ticker']}\n" \
                        f"P/E Ratio: {worst_score['P/E Ratio']:.2f}\n" \
                        f"P/B Ratio: {worst_score['P/B Ratio']:.2f}\n" \
                        f"Debt to Equity: {worst_score['Debt to Equity']:.2f}\n" \
                        f"PEG Ratio: {worst_score['PEG Ratio']:.2f}"
        else:
            output_text = "No valid financial data found for the selected tickers."

        self.output_label.config(text=output_text)


    def start_calculation(self):
        # Run the calculation in a separate thread to keep the UI responsive
        threading.Thread(target=self.calculate).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = PercentageSlidersApp(root)
    root.mainloop()
