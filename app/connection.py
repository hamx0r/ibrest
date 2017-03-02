""" Needs documentation
"""
import time
# from app import log
import logging
import globals as g
#from flask import g
import utils
import handlers
from flask import current_app

__author__ = 'Jason Haury'

log = logging.getLogger(__name__)
# log = utils.setup_logger(log)
#log.setLevel(logging.WARN)

# TODO use single clientId.  Update sync.py for all /order endpoints
def get_client():
    """ Creates a client connection to be used with orders
    """
    # Get client ID from our non-order pool list in memory
    timeout = g.timeout
    while g.clientId_in_use:
        log.debug('Waiting for clientId to become available...({})'.format(timeout))
        time.sleep(0.5)
        timeout -= 1

    client = g.client_pool[g.client_id]

    # Enable logging if we're in debug mode
    if current_app.debug is True:
        client.enableLogging()

    # Reconnect if needed
    if not client.isConnected():
        log.debug('Client {} not connected.  Trying to reconnect...'.format(g.client_id))
        client.disconnect()
        time.sleep(1)
        client.connect()
        # If we failed to reconnect, be sure to put our client ID back in the pool
        if client.isConnected() is False:
            g.clientId_pool.append(g.client_id)
    return client


def setup_client(client):
    """ Attach handlers to the clients
    """
    #log.debug('setup_client {}'.format(client.clientId))
    client.register(handlers.connection_handler, 'ManagedAccounts', 'NextValidId')
    client.register(handlers.history_handler, 'HistoricalData')
    client.register(handlers.order_handler, 'OpenOrder', 'OrderStatus', 'OpenOrderEnd')
    client.register(handlers.portfolio_positions_handler, 'Position', 'PositionEnd')
    client.register(handlers.account_summary_handler, 'AccountSummary', 'AccountSummaryEnd')
    client.register(handlers.account_update_handler, 'UpdateAccountTime', 'UpdateAccountValue', 'UpdatePortfolio',
                    'AccountDownloadEnd')
    client.register(handlers.contract_handler, 'ContractDetails')
    client.register(handlers.executions_handler, 'ExecDetails', 'ExecDetailsEnd', 'CommissionsReport')
    client.register(handlers.error_handler, 'Error')
    # Add handlers for feeds
    client.register(handlers.market_handler, 'TickSize', 'TickPrice')

    # For easier debugging, register all messages with the generic handler
    # client.registerAll(handlers.generic_handler)

    # Be sure we're in a disconnected state
    client.disconnect()


def close_client(client):
    """ Put clientId back into pool but don't close connection
    """
    if client is None:
        log.warn('Trying to close None client')
        return
    client_id = client.clientId
    g.clientId_in_use = False
    return client_id
