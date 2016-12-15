""" Needs documentation
"""
import globals as g
import os
import json
import sync

from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.ext.OrderState import OrderState
import logging

__author__ = 'Jason Haury'

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------
# SHARED FUNCTIONS
# ---------------------------------------------------------------------
def msg_to_dict(msg):
    """ Converts a message to a dict
    """
    d = dict()
    for i in msg.items():
        if isinstance(i[1], (Contract, Order, OrderState)):
            d[i[0]] = i[1].__dict__
        else:
            d[i[0]] = i[1]
    return d


# ---------------------------------------------------------------------
# SYNCHRONOUS RESPONSE MESSAGE HANDLERS
# ---------------------------------------------------------------------
def connection_handler(msg):
    """ Handles messages from when we connect to TWS
    """
    if msg.typeName == 'nextValidId':
        g.orderId = max(int(msg.orderId), g.orderId)
        # log.info('Connection lock released.  OrderId set to {}'.format(g.orderId))
        # g.getting_order_id = False  # Unlock place_order() to now be called again.
        log.info('Updated orderID: {}'.format(g.orderId))
    elif msg.typeName == 'managedAccounts':
        g.managedAccounts = msg.accountsList.split(',')
        log.debug('Updated managed accounts: {}'.format(g.managedAccounts))


def account_summary_handler(msg):
    """ Update our global Account Summary data response dict
    """
    if msg.typeName == 'accountSummary':
        # account = msg_to_dict(msg)
        g.account_summary_resp[int(msg.reqId)][msg.tag] = msg.value
    elif msg.typeName == 'accountSummaryEnd':
        g.account_summary_resp[int(msg.reqId)]['accountSummaryEnd'] = True
    log.debug('SUMMARY: {})'.format(msg))


def account_update_handler(msg):
    """ Update our global Account Update data response dict
    """
    if msg.typeName == 'updateAccountTime':
        g.account_update_resp[msg.typeName] = msg.updateAccountTime
    elif msg.typeName == 'updateAccountValue':
        account = msg_to_dict(msg)
        g.account_update_resp[msg.typeName][msg.key] = account
    elif msg.typeName == 'updatePortfolio':
        account = msg_to_dict(msg)
        g.account_update_resp[msg.typeName].append(account.copy())
    elif msg.typeName == 'accountDownloadEnd':
        g.account_update_resp[msg.typeName] = True
    log.debug('UPDATE: {})'.format(msg))


def portfolio_positions_handler(msg):
    """ Update our global Portfolio Positions data response dict
    """
    if msg.typeName == 'position':
        position = msg_to_dict(msg)
        g.portfolio_positions_resp['positions'].append(position.copy())
    elif msg.typeName == 'positionEnd':
        g.portfolio_positions_resp['positionEnd'] = True
    log.debug('POSITION: {})'.format(msg))


def history_handler(msg):
    """ Update our global history data response dict
    """
    history = msg_to_dict(msg)
    g.history_resp[int(history['reqId'])][msg.date] = history.copy()
    #log.debug('HISTORY: {})'.format(msg))


def order_handler(msg):
    """ Update our global Order data response dict
    """
    if msg.typeName in ['orderStatus', 'openOrder']:
        d = msg_to_dict(msg)
        g.order_resp[msg.typeName].append(d.copy())
        order_msg = g.order_resp_by_order.get(d['orderId'], dict(openOrder=dict(), orderStatus=dict()))
        order_msg[msg.typeName] = d.copy()
        g.order_resp_by_order[d['orderId']] = order_msg
        log.debug('ORDER: {}'.format(d))

    elif msg.typeName == 'openOrderEnd':
        g.order_resp['openOrderEnd'] = True
    log.debug('ORDER: {})'.format(msg))


def error_handler(msg):
    """ Update our global to keep the latest errors available for API returns. Error messages have an id attribute which
    maps to the orderId or tickerId of the request which generated the error.
    https://www.interactivebrokers.com/en/software/api/apiguide/java/error.htm

    IbPy provides and id of -1 for connection error messages
    """
    g.error_resp[msg.id] = {i[0]: i[1] for i in msg.items()}
    log.error('ERROR: {}'.format(msg))

    # TODO if clientId is already in use erroneously, attempt to recover, or generate new clientId
    # If our client connections get out of sync:


def generic_handler(msg):
    log.debug('MESSAGE: {}, {})'.format(msg, msg.keys))


# ---------------------------------------------------------------------
# FEED MESSAGE HANDLERS
# ---------------------------------------------------------------------
def market_handler(msg):
    """ Update our global Market data response dict
    """
    resp = msg_to_dict(msg)
    g.market_resp[int(msg.tickerId)].append(resp.copy())
