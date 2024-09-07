from ibapi.client import *
from ibapi.wrapper import *
import time as true_time
import threading 
import pathlib
import operator
import pprint
import pandas as pd
from datetime import datetime
from datetime import timedelta
from configparser import ConfigParser

from bot import Pybot
from indicator import Indicators
from ib_insync import IB, Stock, MarketOrder, LimitOrder, BarData

import logging
logging.basicConfig(level=logging.DEBUG)

#constants
TWS_Live = 7496
TWS_Paper = 7497
IBG_Live = 4001
IBG_Paper = 4002
PORT = TWS_Paper
HOST = "localhost"


#get config log in values
config = ConfigParser()
config.read('config.ini')

# Inititalize the Bot

trading_robot = Pybot(
       host = HOST,
       port = PORT,
       client_id= 0   
    )

#create new portfolio

trading_robot_portfolio = trading_robot.create_portfolio()

#add multiple postiions to out portfolio
multi_position = [
    {
        'Asset Type': 'equity',
        'quantity': 2,
        'purchase_price': 200.00,
        'Symbol': 'TSLA',
        'purchase_date': '2023-01-31'

    },
    {
        'Asset Type': 'equity',
        'quantity': 2,
        'purchase_price': 200.00,
        'Symbol': 'AAPL',
        'purchase_date': '2023-01-31'

    }
    
]

# Add those positions to the portfolio
new_positions = trading_robot_portfolio.add_positions(positions=multi_position)
pprint.pprint(new_positions)



#add a singal position to the portfolio
trading_robot.portfolio.add_position(
    symbol = 'MSF',
    quantity = 10,
    purchase_price = 200.00,
    asset_type = 'equity',
    purchase_date = '2023-01-31'
)
pprint.pprint(trading_robot.portfolio.positions)


if trading_robot.regular_market_open:
    print("regular market open")
else:
    print("regulare market not open")