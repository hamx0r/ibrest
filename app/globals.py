""" Needs documentation
"""
import os
from ib.opt import ibConnection
import itsdangerous
__author__ = 'Jason Haury'


# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
# Use environment variables
ibgw_host = os.getenv('IBGW_PORT_4003_TCP_ADDR', os.getenv('IBGW_HOST', '127.0.0.1'))
ibgw_port = int(os.getenv('IBGW_PORT_4003_TCP_PORT', os.getenv('IBGW_PORT', '4003')))  # Use 7496 for TWS

# Beacon globals
id_secret_key = os.getenv('ID_SECRET_KEY', None)
serializer = itsdangerous.JSONWebSignatureSerializer(id_secret_key, salt='beacon') if id_secret_key else None
beacon_last_token = None
beacon_current_token = None
current_ip = None

timeout = 20  # Max loops

# Mutables
managedAccounts = []
# TODO use single clientId
clientId_pool = range(1, 8)  # Round-robbin list of clientId's for non-Order tasks.  ID 0 is for orders
clientId_order_in_use = False
client_pool = {c: ibConnection(ibgw_host, ibgw_port, c) for c in [0]+clientId_pool}  # +1 for Order client
getting_order_id = False
orderId = 0
tickerId = 0


# ---------------------------------------------------------------------
# SYNCHRONOUS RESPONSES
# ---------------------------------------------------------------------
# Responses.  Global dicts to use for our responses as updated by Message handlers, keyed by clientId
portfolio_positions_resp = {c: dict() for c in xrange(len(clientId_pool)+1)}
account_summary_resp = {c: dict(accountSummaryEnd=False) for c in xrange(len(clientId_pool)+1)}
account_update_resp = dict(accountDownloadEnd=False, updateAccountValue=dict(), updatePortfolio=[])
# Track errors keyed in "id" which is the orderId or tickerId (or -1 for connection errors)
error_resp = {-1: {"errorCode": 502, "errorMsg": "Couldn't connect to TWS.  Confirm that \"Enable ActiveX and Socket "
                                                 "Clients\" is enabled on the TWS \"Configure->API\" menu.", "id": -1},
              -2: {"errorCode": None, "errorMsg": "Too many requests.  Client ID not available in time.  Try request later", "id": -2}}

# Store contractDetails messages
contract_resp = dict(contractDetailsEnd=False, contractDetails=dict(), bondContractDetails=dict())
# When getting order info, we want it for all clients, and don't care so much if multiple requests try to populate this
order_resp = dict(openOrderEnd=False, openOrder=[], orderStatus=[])
# When placing/deleting orders, we care about what orderId is used.  Key off orderId.
order_resp_by_order = dict()
# Recent Executions
executions_resp = dict(execDetailsEnd=False, execDetails=dict(), commissionReport=dict())


# ---------------------------------------------------------------------
# FEED RESPONSE BUFFERS
# ---------------------------------------------------------------------
# Globals to use for feed responses
market_resp = dict()  # market feed
# Dict of history responses keyed off of reqId (tickerId)
history_resp = dict()

