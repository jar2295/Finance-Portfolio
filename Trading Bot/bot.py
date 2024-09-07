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

logging.basicConfig(level=logging.DEBUG)


class Pybot():

    def __init__(self, host: str, port: int, client_id: int, trading_account: Optional[str] = None) -> None:
        self.trading_account: Optional[str] = trading_account
        self.host: str = host
        self.port: int = port
        self.client_id: int = client_id
        self.ib: IB = self._create_session()  # Properly creates and connects to IB session
        self.trades: Dict[str, Dict] = {}
        self.historical_prices: Dict[str, List[Dict]] = {}
        self.stock_frame = None
        
    def _create_session(self) -> IB:
        """
        Creates and returns a connected IB session.
        """
        util.logToConsole('DEBUG')
        ib = IB()
        try:
            logging.debug('Attempting to connect to IBKR...')
            asyncio.run(self._connect_ib(ib))
            logging.debug('Successfully connected to IBKR.')
        except asyncio.TimeoutError:
            logging.error('Connection to IB timed out.')
            raise ConnectionError('Connection to IB timed out')
        except Exception as e:
            logging.error(f'Error connecting to IB: {e}')
            raise ConnectionError(f'Error connecting to IB: {e}')
        return ib
    
    async def _connect_ib(self, ib: IB):
        """
        Asynchronously connects to IB.
        """
        await ib.connectAsync(self.host, self.port, clientId=self.client_id)

        
    @property
    def pre_market_open(self) -> bool:
        
        pre_market_start_time = datetime.now().replace(hour=12, minute=00, tzinfo=timezone.utc)
        market_start_time = datetime.now().replace(hour=13, minute=30, tzinfo=timezone.utc)
        right_now = datetime.now().replace(tzinfo=timezone.utc).timestamp()

        if market_start_time >= right_now >= pre_market_start_time:
            return True
        else:
            return False
        
    @property
    def post_market_open(self) -> bool:

        post_market_end_time = datetime.now().replace(hour=22, minute=30, tzinfo=timezone.utc)
        market_end_time = datetime.now().replace(hour=20, minute=00, tzinfo=timezone.utc)
        right_now = datetime.now().replace(tzinfo=timezone.utc).timestamp()

        if post_market_end_time >= right_now >= market_end_time:
            return True
        else:
            return False

    @property
    def regular_market_open(self) -> bool:
        market_start_time = datetime.now().replace(hour=13, minute=30, tzinfo=timezone.utc)
        market_end_time = datetime.now().replace(hour=20, minute=0, tzinfo=timezone.utc)
        right_now = datetime.now().replace(tzinfo=timezone.utc)

        if market_start_time <= right_now <= market_end_time:
            return True
        else:
            return False


    
        
    def create_portfolio(self) -> portfolio:
        """
        Initializes and sets up the portfolio with current positions.
        """
        # Initialize portfolio object
        self.portfolio = portfolio(account_number=self.trading_account)
        
        # Assign the IB client to the portfolio
        self.portfolio.ib_client = self.ib
        
        # Fetch current positions and update the portfolio
        positions = self.ib.positions()
        formatted_positions = [{
            'Symbol': position.contract.symbol,
            'Asset Type': position.contract.secType,
            'Quantity': position.position,
            'Purchase Price': position.avgCost,
            'Purchase Date': None  # Placeholder, not directly available from IBKR
        } for position in positions]
        
        self.portfolio.add_positions(formatted_positions)
        
        return self.portfolio
    
    
    def grab_current_quotes(self) -> dict: 
        symbols = self.portfolio.positions.keys()
        quotes = {}

        # Iterate through each symbol to request market data
        for symbol in symbols:
            # Create a Stock object for each symbol
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Request market data asynchronously
            market_data = self.ib.reqMktData(contract, '', False, False)

            # Wait for the data to be received
            self.ib.sleep(1)  # Giving time for data to be fetched

            # Extract relevant information and add to quotes dictionary
            quotes[symbol] = {
                'Last Price': market_data.last,
                'Bid': market_data.bid,
                'Ask': market_data.ask,
                'Timestamp': datetime.now()
            }

        return quotes
        
    
    def create_trade(self):
        pass

    def create_stock_frame(self):
        pass

    

    def grab_histrocial_prices(self) -> List[dict]:
        pass

