from typing import List
from typing import Dict
from typing import Union
from typing import Optional
from typing import Tuple

from ib_insync import IB, Stock, MarketOrder, LimitOrder, BarData

class portfolio():

    def __init__(self, account_number: Optional[str] = None):
        self.positions = {}
        self.positions_count: int = 0
        self.market_value: float = 0.0
        self.profit_loss: float = 0.0
        self.risk_tolerance: float = 0.0
        self.account_number: Optional[str] = account_number
        self.ib_client: Optional[IB] = None
       


    def add_position(self, symbol: str, asset_type: str, purchase_date: Optional[str], quantity: int = 0, purchase_price: float = 0.0) -> Dict[str, dict]:
        """
        Adds a single position to the portfolio.
        """
        if symbol in self.positions:
            # Update existing position
            self.positions[symbol]['quantity'] += quantity
        else:
            # Add new position
            self.positions[symbol] = {
                'Symbol' : symbol,
                'asset_type': asset_type,
                'quantity': quantity,
                'purchase_price': purchase_price,
                'purchase_date': purchase_date
            }
        self.positions_count = len(self.positions)
        return self.positions
        
    def add_positions(self, positions: List[dict]) -> Dict[str, dict]:
        """
        Adds multiple positions to the portfolio.
        """
        if isinstance(positions, list):
            for position in positions:
                self.add_position(
                    symbol=position['Symbol'],
                    asset_type=position['Asset Type'],
                    purchase_date=position.get('Purchase Date', None),
                    purchase_price=position.get('Purchase Price', 0.0),
                    quantity=position.get('Quantity', 0)
                )
            return self.positions
        else:
            raise TypeError("Positions must be a list of dictionaries.")
        

    def remove_position(self, symbol: str) -> Tuple[bool, str]:
        """
        Removes a position from the portfolio by symbol.
        """
        if symbol in self.positions:
            del self.positions[symbol]
            self.positions_count -= 1
            return True, f"{symbol} was successfully removed."
        else:
            return False, f"{symbol} did not exist in the portfolio."

    def in_portfolio(self, symbol: str) -> bool:
        if symbol in self.positions:
            return True
        else:
            return False
        
    def is_profitable(self, symbol:str, current_price: float) -> bool:
        # Get Purchase Price
        purchase_price = self.positions[symbol]["purchase_price"]

        if (purchase_price <= current_price):
            return True
        elif (purchase_price > current_price):
            return False

    @property
    def ib_client(self) -> Optional[IB]:
        """
        Gets the IB object for the portfolio.

        Returns:
        [IB] -- An authenticated session with the IBKR API.
        """
        return self._ib_client

    @ib_client.setter
    def ib_client(self, ib_client: IB) -> None:
        """
        Sets the IB object for the portfolio.

        Arguments:
        ib_client [IB] -- An authenticated session with the IBKR API to be set.
        """
        self._ib_client = ib_client


    
    
    
    def total_allocation(self):
        """
        Calculates total allocation of the portfolio. (Placeholder for implementation)
        """
        pass

    def risk_exposure(self):
        """
        Calculates risk exposure of the portfolio. (Placeholder for implementation)
        """
        pass

    def total_market_value(self):
        """
        Calculates total market value of the portfolio. (Placeholder for implementation)
        """
        pass