""" Needs documentation
"""
import logging
from ib.ext.Contract import Contract

__author__ = 'Jason Haury'
log = logging.getLogger(__name__)


def make_contract(symbol, args=None):
    contract = Contract()
    contract.m_symbol = symbol
    contract.m_secType = 'STK'
    contract.m_exchange = 'SMART'
    #contract.m_primaryExch = 'SMART'  # removed per IB tech
    contract.m_currency = 'USD'
    #contract.m_localSymbol = symbol # removed per IB tech

    if args:
        for attr in dir(contract):
            if attr[:2] == 'm_' and attr[2:] in args:
                val = str(args[attr[2:]])
                log.debug('Setting Contract attribute {}={}'.format(attr, val))
                setattr(contract, attr, val)
    log.debug('Contract details: {}'.format(contract.__dict__))
    return contract


def make_response(resp):
    """ Returns Flask tuple `resp, code` code per http://flask.pocoo.org/docs/0.10/quickstart/#about-responses
    """
    if 'errorMsg' in resp:
        # Error 162 pertains to "Historical data request pacing violation"
        if resp['errorCode'] in [None, 162]:
            return resp, 429
        # Bad request if arg which made it to TWS wasn't right
        return resp, 400
    else:
        return resp


def json_object_hook(data, ignore_dicts=False):
    # if this is a unicode string, return its string representation
    if isinstance(data, unicode):
        return data.encode('utf-8')
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [json_object_hook(item, ignore_dicts=True) for item in data]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            json_object_hook(key, ignore_dicts=True): json_object_hook(value, ignore_dicts=True)
            for key, value in data.iteritems()
            }
    # if it's anything else, return it in its original form
    return data
