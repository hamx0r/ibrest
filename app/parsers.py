""" Flask-RESTful request parsers which help enforce argument needs for IB types:
 * Order
 * Contract
"""
from flask_restful import reqparse

__author__ = 'Jason Haury'

# ---------------------------------------------------------------------
# ORDER PARSER
# ---------------------------------------------------------------------
# Contains all args used for Order objects:
# https://www.interactivebrokers.com/en/software/api/apiguide/java/order.htm
order_parser = reqparse.RequestParser(bundle_errors=True)
# Order args https://www.interactivebrokers.com/en/software/api/apiguide/java/order.htm
# Order types https://www.interactivebrokers.com/en/software/api/apiguide/tables/supported_order_types.htm
order_parser.add_argument('totalQuantity', type=int, required=True, help='Total Quantity to order', store_missing=False)
order_parser.add_argument('minQty', type=int, help='Min Quantity to order', store_missing=False)
order_parser.add_argument('orderId', type=int, help='Order ID', store_missing=False)
order_parser.add_argument('trailingPercent', type=float, help='Trailing Stop percent', store_missing=False)
order_parser.add_argument('action', type=str, required=False, help='Must be BUY, SELL or SSHORT', store_missing=False)
order_parser.add_argument('tif', type=str, help='Time in force', choices=['DAT', 'GTC', 'IOC', 'GTD'], store_missing=False)


# ---------------------------------------------------------------------
# CONTRACT PARSER
# ---------------------------------------------------------------------
# Contains all args used for Contract objects:
# https://www.interactivebrokers.com/en/software/api/apiguide/java/contract.htm
contract_parser = reqparse.RequestParser(bundle_errors=True)
# clientId is handled by sync code
contract_parser.add_argument('symbol', type=str, required=False, help='Stock ticker symbol to order', store_missing=False)
contract_parser.add_argument('orderType', type=str, required=False, help='Type of Order to place',
                             choices=['LMT', 'MTL', 'MKT PRT', 'QUOTE', 'STP', 'STP LMT', 'TRAIL LIT', 'TRAIL MIT',
                                      'TRAIL', 'TRAIL LIMIT', 'MKT', 'MIT', 'MOC', 'MOO', 'PEG MKT', 'REL', 'BOX TOP',
                                      'LOC', 'LOO', 'LIT', 'PEG MID', 'VWAP', 'GAT', 'GTD', 'GTC', 'IOC', 'OCA', 'VOL'], store_missing=False)
contract_parser.add_argument('secType', type=str, required=False, default='STK', help='Security Type',
                             choices=['STK', 'OPT', 'FUT', 'IND', 'FOP', 'CASH', 'BAG', 'NEWS'], store_missing=False)
contract_parser.add_argument('exchange', type=str, required=False, default='SMART', help='Exchange (ie NASDAQ, SMART)', store_missing=False)
contract_parser.add_argument('currency', type=str, required=False, default='USD',
                             help='Currency used for order (ie USD, GBP))', store_missing=False)
# not needed for updates:
contract_parser.add_argument('symbol', type=str, required=False, help='Stock ticker symbol to order', store_missing=False)
