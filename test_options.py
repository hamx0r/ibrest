""" Needs documentation
"""
__author__ = 'Jason Haury'

from ib.opt import ibConnection
from app import connection
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.ext.ComboLeg import ComboLeg


host = 'localhost'
port = 7497
client = ibConnection(host, port, 0)
connection.setup_client(client)
client.connect()

con1 = Contract()
con1.m_symbol = "GOOG"
con1.m_secType = 'OPT'
con1.m_expiry = "201701"
con1.m_strike = 775.0
con1.m_right = 'C'
con1.m_multiplier = "100"
con1.m_exchange = 'SMART'
con1.m_currency = "USD"
print client.reqContractDetails(1, con1)