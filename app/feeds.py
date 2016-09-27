""" In case of IB EClientSocket requests which generate continuous feeds of data, this module will generate atom feeds.

This is accomplished by storing data in a Sqlite3 DB
"""
import logging
import time
from datetime import datetime, timedelta

import connection
import globals as g
import utils
from connection import get_client, close_client
from ib.ext.Contract import Contract
from sync import log
from utils import make_contract

__author__ = 'Jason Haury'
log = logging.getLogger(__name__)


# log = utils.setup_logger(log)
def get_tickerId():
    """ Returns next valid ticker ID in a way which won't overlap with recent orderIds in the error responses"""

    g.tickerId += 1
    # Since error messages key off `id` being both an orderId or tickerId depending on context, we may have overlapping
    # `id`'s between our feeds and sync functions.  As a safety, keep our either much larger or much lower than our
    # orderId since we can't control orderId
    id_threshold = 10000
    if g.orderId < id_threshold:
        if g.tickerId < id_threshold:
            g.tickerId += id_threshold
    elif g.tickerId > id_threshold:
        # our orderId is >= id_threshold
        g.tickerId -= id_threshold
    return g.tickerId


# ---------------------------------------------------------------------
# MARKET DATA FUNCTIONS
# ---------------------------------------------------------------------
# TODO This needs to be a feed, not an endpoint.   http://flask.pocoo.org/snippets/10/.
def get_market_data(symbol, args):
    """ The m_symbol for the contract is all our API takes from user (for now).
    User must have appropriate IB subscriptions.
    https://www.interactivebrokers.com/en/software/api/apiguide/java/reqmktdata.htm
    """
    # TODO consider taking more args to get our market data with: filter (price, size, optionComputation, etc) and desired length of data.  Also, tick lists
    log.debug('Getting market data for {}'.format(symbol))
    # Connect to TWS
    client = get_client()
    if client.isConnected() is False:
        return {'error': 'Not connected to TWS'}
    log.debug('Creating Contract for symbol {}'.format(symbol))
    contract = make_contract(str(symbol), args)  # , prim_exch='NASDAQ')

    our_tickerId = get_tickerId()
    g.market_resp[our_tickerId] = []
    log.info('Requesting market data')
    client.reqMktData(our_tickerId, contract, '', False)
    timeout = g.timeout
    while len(g.market_resp[our_tickerId]) < 5 and client.isConnected() is True and timeout > 0:
        log.info("Waiting for responses on {}...".format(client))
        time.sleep(0.25)
        timeout -= 1
    client.cancelMktData(our_tickerId)
    log.debug('Disconnected Market client {}'.format(close_client(client)))
    return g.market_resp.pop(our_tickerId)


# ---------------------------------------------------------------------
# HISTORY FUNCTIONS
# ---------------------------------------------------------------------
# TODO move this to sync.py since it is not really a feed (it provides a `finished` message)
def get_history(symbol, args):
    """ Args may be any of those in reqHistoricalData()
    https://www.interactivebrokers.com/en/software/api/apiguide/java/reqhistoricaldata.htm
    """
    log.debug('history symbol {}, args: {}'.format(symbol, args))

    client = connection.get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    # Populate contract with appropriate
    contract = utils.make_contract(str(symbol), args)

    # log.debug('contract: {}'.format(contract))

    our_tickerId = get_tickerId()
    g.history_resp[our_tickerId] = dict()
    g.error_resp[our_tickerId] = None
    # endtime = (datetime.now() - timedelta(minutes=15)).strftime('%Y%m%d %H:%M:%S')
    log.debug('requesting historical data')
    req_dict = dict(tickerId=our_tickerId,
                    contract=contract,
                    endDateTime=str(args.get('endDateTime', datetime.now().strftime('%Y%m%d %H:%M:%S'))),
                    durationStr=str(args.get('durationStr', '1 D')),
                    barSizeSetting=str(args.get('barSizeSetting', '1 min')),
                    whatToShow=args.get('whatToShow', 'TRADES'),
                    useRTH=int(args.get('useRTH', 0)),
                    formatDate=int(args.get('formatDate', 2))
                    )
    log.debug('req_dict {}'.format(req_dict))
    client.reqHistoricalData(**req_dict)

    """
    durationStr='60 S',
    barSizeSetting='1 min',
    whatToShow='TRADES',
    useRTH=0,
    formatDate=1)
    """
    log.debug('waiting for historical data)')
    timeout = g.timeout
    while not any(
            ["finished" in h for h in g.history_resp[our_tickerId].keys()]) and client.isConnected() and timeout > 0:
        log.debug("Waiting for History responses on client {}...".format(client.clientId))
        if g.error_resp.get(our_tickerId, None) is not None:
            # An errorCode of 366 seen on IBGW logs is often meaningless since it shows up for every history call several
            # seconds after it's already found data and receive the "finished" message.  If data
            # did exist, then it would be returned before the error message was generated
            connection.close_client(client)
            return g.error_resp[our_tickerId]
        elif client.isConnected() is False:
            return {'errorMsg': 'Connection lost'}
        time.sleep(0.25)
        timeout -= 1
    # log.debug('history: {}'.format(g.history_resp))
    log.debug('closing historical data stream')
    client.cancelHistoricalData(our_tickerId)
    connection.close_client(client)
    return g.history_resp.pop(our_tickerId)
