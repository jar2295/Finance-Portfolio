import pandas as pd

from datetime import datetime
from datetime import time
from datetime import timezone

from typing import List
from typing import Dict
from typing import Union
from typing import Optional

from portfolio import portfolio

from ib_insync import IB, util, Stock, MarketOrder, LimitOrder, BarData
import asyncio
import logging

logging.disable(logging.CRITICAL)


from ib_insync import IB, Stock
import asyncio
import logging

logging.disable(logging.CRITICAL)


class Pybot:
    def __init__(self, host: str, port: int, client_id: int, trading_account: Optional[str] = None) -> None:
        print("Initializing Pybot...")  # Debugging statement
        self.trading_account: Optional[str] = trading_account
        self.host: str = host
        self.port: int = port
        self.client_id: int = client_id
        self.ib: IB = IB()  # Create IB instance
        self.trades: Dict[str, Dict] = {}
        self.historical_prices: Dict[str, List[Dict]] = {}
        self.stock_frame = None
        self.portfolio = None
        self.connected = False

    async def connect(self):
        """
        Asynchronously connects to IB and maintains the connection.
        """
        print("Attempting to connect to IB...")
        while not self.connected:
            try:
                await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
                await asyncio.sleep(1)  # Short delay to ensure connection establishment
                if self.ib.isConnected():
                    self.connected = True
                    print("Connected to IB.")
                else:
                    print("Failed to connect to IB. Retrying...")
            except Exception as e:
                logging.error(f"Error connecting to IB: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def disconnect(self):
        """
        Asynchronously disconnects from IB.
        """
        if self.ib.isConnected():
            self.ib.disconnect()
            self.connected = False
            print("Disconnected from IB.")

    async def main_loop(self):
        """
        Main loop for running tasks.
        """
        try:
            await self.connect()
            while self.connected:
                # Replace this with your actual bot tasks
                print("Running bot tasks...")
                # Example task
                await self.perform_tasks()
                await asyncio.sleep(10)  # Adjust sleep time as needed
        finally:
            await self.disconnect()

    def is_connected(self) -> bool:
        return self.ib.isConnected()

    @property
    def pre_market_open(self) -> bool:
        pre_market_start_time = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
        market_start_time = datetime.now(timezone.utc).replace(hour=13, minute=30, second=0, microsecond=0)
        right_now = datetime.now(timezone.utc)
        return pre_market_start_time <= right_now < market_start_time

    @property
    def post_market_open(self) -> bool:
        market_end_time = datetime.now(timezone.utc).replace(hour=20, minute=0, second=0, microsecond=0)
        post_market_end_time = datetime.now(timezone.utc).replace(hour=22, minute=30, second=0, microsecond=0)
        right_now = datetime.now(timezone.utc)
        return post_market_end_time >= right_now >= market_end_time

    @property
    def regular_market_open(self) -> bool:
        market_start_time = datetime.now().replace(hour=13, minute=30, tzinfo=timezone.utc)
        market_end_time = datetime.now().replace(hour=20, minute=0, tzinfo=timezone.utc)
        right_now = datetime.now().replace(tzinfo=timezone.utc)
        return market_start_time <= right_now <= market_end_time

    def create_portfolio(self) -> portfolio:
        self.portfolio = portfolio(account_number=self.trading_account)
        self.portfolio.ib_client = self.ib
        positions = self.ib.positions()
        formatted_positions = [{
            'Symbol': position.contract.symbol,
            'Asset Type': position.contract.secType,
            'Quantity': position.position,
            'Purchase Price': position.avgCost,
            'Purchase Date': None
        } for position in positions]
        self.portfolio.add_positions(formatted_positions)
        return self.portfolio

    async def grab_current_quotes(self) -> dict:
        if not self.is_connected():
            raise ConnectionError("IB client is not connected.")
        
        symbols = self.portfolio.positions.keys()
        quotes = {}
        for symbol in symbols:
            contract = Stock(symbol, 'SMART', 'USD')
            market_data = self.ib.reqMktData(contract, '', False, False)
            timeout = 10
            start_time = datetime.now()
            while True:
                await asyncio.sleep(1)
                # Print debug information for market data
                print(f"Checking market data for {symbol}: Last Price: {market_data.last}, Bid: {market_data.bid}, Ask: {market_data.ask}")
                if market_data.last is not None and market_data.bid is not None and market_data.ask is not None:
                    break
                if (datetime.now() - start_time).total_seconds() > timeout:
                    logging.warning(f"Timeout while waiting for data for {symbol}")
                    break
            
            # Log the data retrieval
            logging.info(f"Data for {symbol}: Last Price: {market_data.last}, Bid: {market_data.bid}, Ask: {market_data.ask}")

            quotes[symbol] = {
                'Last Price': market_data.last if market_data.last is not None else 'N/A',
                'Bid': market_data.bid if market_data.bid is not None else 'N/A',
                'Ask': market_data.ask if market_data.ask is not None else 'N/A',
                'Timestamp': datetime.now()
            }
            self.ib.cancelMktData(market_data)
        
        # Log the final quotes
        logging.info(f"Final quotes: {quotes}")

        return quotes
