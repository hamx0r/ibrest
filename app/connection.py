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
def get_client(client_id=None):
    """ Creates a client connection to be used with orders
    """
    if client_id is None:
        # Get client ID from our non-order pool list in memory
        log.info('Current clients available: {}'.format(g.clientId_pool))
        timeout = g.timeout
        while len(g.clientId_pool) == 0 and timeout > 0:
            log.debug('Waiting for clientId to become available...({})'.format(timeout))
            time.sleep(0.5)
            timeout -= 1
        try:
            client_id = g.clientId_pool.pop(0)
        except IndexError:
            log.error('Error popping client from pool')
            client_id = None
    elif client_id == 0:
        # Special case client_id because this is for orders only
        # Sometimes the client disconnects due to another error.  If it's not connected, assume such an error happened
        client = g.client_pool[client_id]
        #log.debug('Client 0 = {}'.format(client))
        if not client.isConnected():
            log.warn('Client 0 was disonnected.  Attempting reconnection')
            client.disconnect()
            time.sleep(1)
            client.connect()
            g.clientId_order_in_use = False
            return client

        # At this point, we had a connected client, so use our lock as usual
        timeout = g.timeout
        if g.clientId_order_in_use:
            while g.clientId_order_in_use and timeout > 0:
                log.debug('Waiting for clientId 0 to become available...({})'.format(client_id, timeout))
                time.sleep(0.5)
                timeout -= 1
        # Set order client to in use
        if g.clientId_order_in_use is False:
            g.clientId_order_in_use = True
        else:
            log.error('Client 0 was tied up for too long')
            client_id = None

    else:
        # A client ID was specified, so wait for it to become available if it's not already
        # First, make sure our client_id is valid
        if client_id not in range(1, 8):
            log.error('client_id out of range: {}'.format(client_id))
            return
        timeout = g.timeout
        while client_id not in g.clientId_pool and timeout > 0:
            log.info('Waiting for clientId {} to become available...({})'.format(client_id, timeout))
            time.sleep(0.5)
            timeout -= 1
        try:
            g.clientId_pool.pop(g.clientId_pool.index(client_id))
        except:
            client_id = None

    if client_id is None:
        log.error('Unable to connect to client.')
        return

    log.debug('Attempting connection with client_id {} at {}:{}'.format(client_id, g.ibgw_host, g.ibgw_port))
    client = g.client_pool[client_id]

    # Enable logging if we're in debug mode
    if current_app.debug is True:
        client.enableLogging()

    # Reconnect if needed
    if not client.isConnected():
        log.debug('Client {} not connected.  Trying to reconnect...'.format(client_id))
        client.disconnect()
        time.sleep(1)
        client.connect()
        # If we failed to reconnect, be sure to put our client ID back in the pool
        if client.isConnected() is False:
            g.clientId_pool.append(client_id)
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
    client.register(handlers.error_handler, 'Error')
    # Add handlers for feeds
    client.register(handlers.market_handler, 'TickSize', 'TickPrice')
    # Be sure we're in a disconnected states
    client.disconnect()


def close_client(client):
    """ Put clientId back into pool but don't close connection
    """
    if client is None:
        log.warn('Trying to close None client')
        return
    client_id = client.clientId
    # We only add non-0 clients back to our pool
    if client_id == 0:
        g.clientId_order_in_use = False
    else:
        # Add our client_id onto end of our pool
        g.clientId_pool.append(client_id)
    return client_id
