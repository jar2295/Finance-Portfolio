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
import asyncio
import logging
logging.disable(logging.CRITICAL)

asyncio.get_event_loop().set_debug(True)
#constants
TWS_Live = 7496
TWS_Paper = 7497
IBG_Live = 4001
IBG_Paper = 4002
PORT = TWS_Paper
HOST = "localhost"

async def test_connection():
    ib = IB()
    try:
        await ib.connectAsync('localhost', 7497, clientId=0)
        print("Connected to IB.")
        print(f"Connection status: {ib.isConnected()}")
        await asyncio.sleep(10)  # Keep the connection open for 10 seconds
    except Exception as e:
        print(f"Error connecting to IB: {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("Disconnected from IB.")

asyncio.run(test_connection())

async def main():
    print("Starting bot...")  # Debugging statement


    # Initialize the Bot
    print("Initializing trading_robot...")  # Debugging statement
    trading_robot = Pybot(
        host="localhost",
        port=7497,
        client_id=0
    )

    # Connect to IB
    await trading_robot.connect()

    # Create new portfolio
    print("Creating portfolio...")  # Debugging statement
    trading_robot_portfolio = trading_robot.create_portfolio()

    # Add multiple positions to our portfolio
    print("Adding positions...")  # Debugging statement
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
    new_positions = trading_robot_portfolio.add_positions(positions=multi_position)
    pprint.pprint(new_positions)

    # Add a single position to the portfolio
    print("Adding single position...")  # Debugging statement
    trading_robot.portfolio.add_position(
        symbol='MSF',
        quantity=10,
        purchase_price=200.00,
        asset_type='equity',
        purchase_date='2023-01-31'
    )
    pprint.pprint(trading_robot.portfolio.positions)

    print("Checking market status...")  # Debugging statement
    if trading_robot.regular_market_open:
        print("Regular market open")
    else:
        print("Regular market not open")

    if trading_robot.pre_market_open:
        print("Pre-market open")
    else:
        print("Pre-market not open")

    if trading_robot.post_market_open:
        print("Post-market open")
    else:
        print("Post-market not open")

    # Fetch the current quotes in our portfolio
    print("Fetching current quotes...")  # Debugging statement
    current_quotes = await trading_robot.grab_current_quotes()
    pprint.pprint(current_quotes)

    await trading_robot.disconnect() 

# Run the main function
asyncio.run(main())