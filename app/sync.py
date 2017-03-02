""" Synchronous wrapper on IbPy to do heavy lifting for our Flask app.
This module contains all IB client handling, even if connection will be used for a feed
"""
import connection
import globals as g

# from flask import g
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.ext.ComboLeg import ComboLeg
from ib.ext.ExecutionFilter import ExecutionFilter
import time
import logging

__author__ = 'Jason Haury'

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# ORDER FUNCTIONS
# ---------------------------------------------------------------------
def get_open_orders():
    """ Uses reqAllOpenOrders to get all open orders from 
    """
    client = connection.get_client(0)
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    # Reset our order resp to prepare for new data
    g.order_resp = dict(openOrderEnd=False, openOrder=[], orderStatus=[])
    client.reqAllOpenOrders()
    timeout = g.timeout
    while g.order_resp['openOrderEnd'] is False and client.isConnected() is True and timeout > 0:
        # log.debug("Waiting for Open Orders responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    connection.close_client(client)
    return g.order_resp


def cancel_order(orderId):
    """ Uses cancelOrder to cancel an order.  The only response is what comes back right away (no EWrapper messages)
    """
    g.error_resp[orderId] = None  # Reset our error for later

    client = connection.get_client(0)
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    log.info('Cancelling order {}'.format(orderId))
    # Reset our order resp to prepare for new data
    g.order_resp_by_order[orderId] = dict(openOrder=dict(), orderStatus=dict())
    client.cancelOrder(int(orderId))
    timeout = g.timeout
    while len(g.order_resp_by_order[orderId]['orderStatus']) == 0 and client.isConnected() is True and timeout > 0:
        # log.debug("Waiting for Cancel Order responses on client {}...".format(client.clientId))
        if g.error_resp[orderId] is not None:
            connection.close_client(client)
            return g.error_resp[orderId]
        time.sleep(0.25)
        timeout -= 1
    connection.close_client(client)
    resp = g.order_resp.copy()
    # Cancelling an order also produces an error, we'll capture that here too
    resp['error'] = g.error_resp[orderId]
    return resp


def wait_for_responses(order_ids, client, timeout,
                       status_list=['Filled', 'Submitted', 'Presubmitted', 'Cancelled']):
    """ Takes a set of 'order_ids' and waits 'timeout' quarter-seconds for some kind of response (error or other) from
    the open client connection.

    'status_list' is list of string includeing: Filled, Submitted, Presubmitted, Cancelled
    It dictates the order status levels that are sufficient to consider a response complete.

    Some orderIDs we don't want to wait for them to get a status in status_list, but simply want to have _something_
    to return.
    """
    # Reset our global order resp dicts to prepare for new data
    for orderId in order_ids:
        g.order_resp_by_order[orderId] = dict(openOrder=dict(), orderStatus=dict())
        g.error_resp[orderId] = None  # Reset our error for later

    # The only response for placing an order is an error, so we'll check for open orders and wait for this orderId or
    # and error to show up.
    client.reqOpenOrders()

    resp = {}
    errors = {}
    while order_ids and client.isConnected() is True and timeout > 0:
        new_order_ids = order_ids.copy()
        log.debug("Waiting for orderIds {} responses for {} more times...".format(order_ids, timeout))
        for orderId in order_ids:
            if g.order_resp_by_order[orderId]['orderStatus'].get('status', None):
                order_resp = g.order_resp_by_order[orderId]
                partial_resp = {'status': order_resp['orderStatus']['status']}
                for k_o in ['m_totalQuantity', 'm_orderType', 'm_trailingPercent', 'm_auxPrice', 'm_lmtPrice']:
                    try:
                        partial_resp[k_o] = order_resp['openOrder']['order'][k_o]
                    except:
                        pass
                # Clean up further
                if partial_resp.get('m_orderType', 'TRAIL') != 'TRAIL':
                    partial_resp.pop('m_trailingPercent')
                try:
                    avgFillPrice = order_resp['openOrder']['order']['avgFillPrice']
                except:
                    avgFillPrice = 0.0
                # Add in Contract info
                try:
                    partial_resp['m_symbol'] = order_resp['openOrder']['contract']['m_symbol']
                except:
                    pass
                # We complete our partial response for a symbol once its status is in `status_list`
                if partial_resp['status'] in status_list:
                    if avgFillPrice != 0.0: partial_resp['avgFillPrice'] = avgFillPrice
                    new_order_ids.discard(orderId)
                    # log.debug('Order Status: {}'.format(order_resp['orderStatus']))
                    log.debug('Order {} partial response: {}'.format(orderId, partial_resp))
                # # Merge in our responses to make a single response dict
                resp[orderId] = partial_resp.copy()
            elif g.error_resp[orderId] is not None:
                log.error('Error placing order: {}'.format(g.error_resp[orderId]))
                errors[orderId] = g.error_resp[orderId].copy()
                new_order_ids.discard(orderId)
        # Always remove orderIds which we should only look once for if we have _something_ to return
        collected_ids = set(resp.keys())
        new_order_ids = new_order_ids - collected_ids
        order_ids = new_order_ids.copy()
        time.sleep(0.25)
        timeout -= 1
        # request a new set of open orders every second
        if timeout % 4 == 0:
            client.reqOpenOrders()

    # add in any errors we may have found
    if errors:
        log.error('Found these order errors: {}'.format(errors))
        resp['errors'] = errors
    return resp


def place_order(order_list):
    """ Auto-detects which args should be assigned to a new Contract or Order, then use to place order.
    Makes use of globals to set initial values, but allows args to override (ie clientId)

    To modify and order, the following parameters are needed (IB won't complain if some of these are missing, but the
    order update won't succeed):
    * orderId
    * exchange
    * totalQuantity
    * secType
    * action
    * orderType AND related paramters (ie TRAIL needs trailingPercent)
    * symbol
    * currency
    * exchange

    When an object in `order_list` has secType = 'BAG', it implies an Options combo order will be placed, requiring
    comboLegs: a JSON list of details required for this function to fetch the conId to then build the ComboLeg.
    """
    log.debug('Starting place_order with args_list: {}'.format(order_list))
    client = connection.get_client(0)
    if client is None:
        connection.close_client(client)
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    # To allow for bracketed orders (or processing a string of orders in a single request), we expect args to be a list
    if not isinstance(order_list, list):
        order_list = [order_list]

    parentId = None
    order_ids = set()
    dont_wait_order_ids = set()  # Some orders aren't worth waiting for responses on
    for args in order_list:
        # If an orderId was provided, we'll be updating an existing order, so only send attributes which are updatable:
        # totalQuantity, orderType, symbol, secType, action
        # TODO consider casting unicode to utf-8 here.  Otherwise we get error(id=1, errorCode=512, errorMsg=Order Sending Error - char format require string of length 1)
        # log.debug('Processing args from order_list: {}'.format(args))
        orderId = args.get('orderId', None)
        if orderId is None:
            orderId = g.orderId
            g.orderId += 1
        order_ids.add(orderId)
        if 'goodAfterTime' in args:
            dont_wait_order_ids.add(orderId)
        contract = Contract()
        order = Order()

        # Populate contract with appropriate args
        for attr in dir(contract):
            if attr[:2] == 'm_' and attr[2:] in args:
                setattr(contract, attr, args[attr[2:]])
        # Populate order with appropriate
        order.m_clientId = client.clientId
        for attr in dir(order):
            if attr[:2] == 'm_' and attr[2:] in args:
                setattr(order, attr, args[attr[2:]])

        # Option Combo Orders need the comboLegs details turned into actual ComboLeg objects
        comboLegs = args.get('comboLegs', None)
        if comboLegs:
            # We need to build ComboLegs by first fetching the conId from the contract details
            all_legs = []
            req_ids = []
            # Clear out our global ContractDetails so our handler can repopulate them
            g.contract_resp['contractDetails'] = dict()
            g.contract_resp['contractDetailsEnd'] = False

            # Request new ContractDetails so we can get the conIds needed for our legs
            for idx, leg in enumerate(comboLegs):
                # Each leg is a dict of details needed to make a ComboLeg object
                leg_contract = Contract()

                # Populate leg_contract with appropriate args
                for attr in dir(leg_contract):
                    if attr[:2] == 'm_' and attr[2:] in leg:
                        setattr(leg_contract, attr, leg[attr[2:]])

                # Fetch conId for leg_contract
                client.reqContractDetails(idx, leg_contract)
                req_ids.append(idx)

            # We've now requested ContractDetails for all legs.  Wait to get their async responses.
            timeout = g.timeout
            while g.contract_resp['contractDetailsEnd'] is False and client.isConnected() is True and timeout > 0:
                time.sleep(0.25)
                timeout -= 1

            # Create our ComboLegs for our order
            for idx, leg in enumerate(comboLegs):
                combo_leg = ComboLeg()
                # Populate combo_leg with appropriate args
                for attr in dir(combo_leg):
                    if attr[:2] == 'm_' and attr[2:] in leg:
                        setattr(combo_leg, attr, leg[attr[2:]])
                combo_leg.m_conId = g.contract_resp['contractDetails'][idx]['m_summary'].m_conId
                all_legs.append(combo_leg)
            contract.m_comboLegs = all_legs

        # If this is a bracketed order, we'll need to add in the parentId for children orders
        if parentId:
            order.m_parentId = parentId

        log.debug('Placing order # {} on client # {} (connected={}): {}'.format(orderId, client.clientId,
                                                                                client.isConnected(), args))
        client.placeOrder(orderId, contract, order)
        # Assume our 1st order in the list is the parent.  Use this for remaining bracket orders and also error handling
        if not parentId:
            parentId = orderId
            log.debug('Setting child order parentId={}'.format(parentId))

    log.debug('Ignoring responses for these orderIds: {}'.format(dont_wait_order_ids))
    order_ids = order_ids - dont_wait_order_ids

    # Don't look for order status or errors until we actually transmit the last order, but then look for status for
    # all order_ids
    timeout = g.timeout
    resp = wait_for_responses(order_ids, client, timeout)
    connection.close_client(client)
    return resp


def place_order_oca(order_list):
    """ Places a Bracket-like OCA set of orders.

    The 1st item in `order_list` is to open a position, and all remaining orders in list
    are an OCA group to close the position.  IBREST creates the OCA group name by using the orderId.

    Auto-detects which args should be assigned to a new Contract or Order, then use to place order.
    Makes use of globals to set initial values, but allows args to override (ie clientId)

    To modify and order, the following parameters are needed (IB won't complain if some of these are missing, but the
    order update won't succeed):
    * orderId
    * exchange
    * totalQuantity
    * secType
    * action
    * orderType AND related paramters (ie TRAIL needs trailingPercent)
    * symbol
    * currency
    * exchange


    Setting `oca` to True implies
    """
    log.debug('Starting place_order_oca with args_list: {}'.format(order_list))
    client = connection.get_client(0)
    if client is None:
        connection.close_client(client)
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    # To allow for bracketed orders (or processing a string of orders in a single request), we expect args to be a list
    if not isinstance(order_list, list):
        log.error('place_order_oca requires list of orders')
        return

    # Our 1st order in the list opens a position.  The rest close it, but are only placed once the 1st order is Filled.
    oca_list = []
    ocaGroup = None
    order_ids = set()
    dont_wait_order_ids = set()  # Some orders aren't worth waiting for responses on
    for args in order_list:
        # If an orderId was provided, we'll be updating an existing order, so only send attributes which are updateable:
        # totalQuantity, orderType, symbol, secType, action
        # TODO consider casting unicode to utf-8 here.  Otherwise we get error(id=1, errorCode=512, errorMsg=Order Sending Error - char format require string of length 1)
        # log.debug('Processing args from order_list: {}'.format(args))
        orderId = args.get('orderId', None)
        if orderId is None:
            orderId = g.orderId
            g.orderId += 1
        if 'goodAfterTime' in args:
            dont_wait_order_ids.add(orderId)
        contract = Contract()
        order = Order()

        # Populate contract with appropriate args
        for attr in dir(contract):
            if attr[:2] == 'm_' and attr[2:] in args:
                setattr(contract, attr, args[attr[2:]])
        # Populate order with appropriate
        order.m_clientId = client.clientId
        for attr in dir(order):
            if attr[:2] == 'm_' and attr[2:] in args:
                setattr(order, attr, args[attr[2:]])

        # If this is a bracketed order, we'll need to add in the ocaGroup for children orders
        if ocaGroup:
            # Use our ocaGroup as the OCA group name.
            # The 1st order won't have this because its an Open order
            # All remaining orders are Close orders in an OCA group, which we'll store to file for later use
            order_ids.add(orderId)
            order.m_ocaType = 1
            order.m_ocaGroup = str(ocaGroup)
            oca_list.append((orderId, contract, order))
            # Don't actually place this OCA order just yet
            continue

        log.debug('Placing Open order # {} on client # {} (connected={}): {}'.format(orderId, client.clientId,
                                                                                     client.isConnected(), args))
        client.placeOrder(orderId, contract, order)
        # Assume our 1st order in the list is the parent.  Use this for remaining bracket orders and also error handling
        if not ocaGroup:
            ocaGroup = orderId
            log.debug('Setting ocaGroup={}'.format(ocaGroup))

    # The only response for placing an order is an error, so we'll check for open orders and wait for this orderId or
    # and error to show up.


    # At this point, our Open order has been placed.  Look for it to be Filled, then place OCA orders.
    # The User must set a goodTillDate on their open order to keep it from filling >1min into the future, or else this
    # function will have given up waiting for it to be filled, and not set the closing OCA group.
    resp = dict()

    timeout = 60 / 0.25

    order_ids = order_ids - dont_wait_order_ids
    # Make a 1-item set representing our Open postion order
    oca_set = set([ocaGroup])
    resp['open_resp'] = wait_for_responses(oca_set, client, timeout, ['Filled'])
    # Our open order is filled, so now place our OCA group close orders
    log.debug('Placing OCA group of {} orders, ignoring responses for these orderIds: {}'.
              format(len(oca_list), dont_wait_order_ids))
    for o in oca_list:
        client.placeOrder(*o)
    # Now get responses for these new OCA orders
    resp['close_resp'] = wait_for_responses(order_ids, client, timeout)
    connection.close_client(client)
    return resp


# ---------------------------------------------------------------------
# ACCOUNT & PORTFOLIO FUNCTIONS
# ---------------------------------------------------------------------
def get_portfolio_positions():
    client = connection.get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]
    g.portfolio_positions_resp = dict(positionEnd=False, positions=[])
    client.reqPositions()
    timeout = g.timeout
    while g.portfolio_positions_resp['positionEnd'] is False and client.isConnected() is True and timeout > 0:
        # log.debug("Waiting for Portfolio Positions responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    client.cancelPositions()
    connection.close_client(client)
    return g.portfolio_positions_resp


def get_account_summary(tags):
    """ Calls reqAccountSummary() then listens for accountSummary messages()
    """
    client = connection.get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]
    client_id = client.clientId
    g.account_summary_resp[client_id] = dict(accountSummaryEnd=False)
    client.reqAccountSummary(client_id, 'All', tags)
    timeout = g.timeout
    while g.account_summary_resp[client_id]['accountSummaryEnd'] is False \
            and client.isConnected() is True \
            and timeout > 0:
        # log.debug("Waiting for Account Summary responses on client {}...".format(client.clientId))
        time.sleep(0.25)
        timeout -= 1
    # time.sleep(1)
    client.cancelAccountSummary(client_id)
    connection.close_client(client)
    return g.account_summary_resp[client_id]


def get_account_update(acctCode):
    """ Calls reqAccountUpdates(subscribe=False) then listens for accountAccountTime/AccountValue/Portfolio messages
    """
    client = connection.get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]
    client_id = client.clientId
    g.account_update_resp = dict(accountDownloadEnd=False, updateAccountValue=dict(), updatePortfolio=[])
    log.debug('Requesting account updates for {}'.format(acctCode))
    client.reqAccountUpdates(subscribe=False, acctCode=acctCode)
    timeout = g.timeout
    while g.account_update_resp['accountDownloadEnd'] is False and client.isConnected() is True and timeout > 0:
        # log.debug("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(.25)
        timeout -= 1
        log.debug('Current update {}'.format(g.account_update_resp))
    client.cancelAccountSummary(client_id)
    connection.close_client(client)
    return g.account_update_resp


def get_executions(args):
    """Gets all (filtered) executions from last 24hrs """
    client = connection.get_client()
    if client is None:
        return g.error_resp[-2]
    elif client.isConnected() is False:
        return g.error_resp[-1]

    g.executions_resp = dict(execDetailsEnd=False, execDetails=[], commissionReport=dict())
    log.debug('Requesting executions for filter {}'.format(args))
    filter = ExecutionFilter()
    for attr in dir(filter):
        if attr[:2] == 'm_' and attr[2:] in args:
            setattr(filter, attr, args[attr[2:]])
    log.debug('Filter: {}'.format(filter.__dict__))
    filter.m_clientId = 0
    client.reqExecutions(1, filter)
    timeout = g.timeout / 2
    while g.executions_resp['execDetailsEnd'] is False and client.isConnected() is True and timeout > 0:
        # log.debug("Waiting for responses on client {}...".format(client.clientId))
        time.sleep(.25)
        timeout -= 1
        log.debug('Current executions {}'.format(g.executions_resp))
    connection.close_client(client)
    return g.executions_resp
