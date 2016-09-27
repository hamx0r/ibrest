#!/usr/bin/env python
""" generated source for module TagValue """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib.overloading import overloaded
from ib.ext.Util import Util

# 
#  * UnderComp.java
#  *
#  
# package: com.ib.client
class TagValue(object):
    """ generated source for class TagValue """
    m_tag = ""
    m_value = ""

    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        pass

    @__init__.register(object, str, str)
    def __init___0(self, p_tag, p_value):
        """ generated source for method __init___0 """
        self.m_tag = p_tag
        self.m_value = p_value

    def __eq__(self, p_other):
        """ generated source for method equals """
        if self is p_other:
            return True
        if p_other is None:
            return False
        l_theOther = p_other
        if Util.StringCompare(self.m_tag, l_theOther.m_tag) != 0 or Util.StringCompare(self.m_value, l_theOther.m_value) != 0:
            return False
        return True

