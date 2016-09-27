Using GUI frameworks and Threads - how to use IbPy with various GUI frameworks and threading models

# GUI Frameworks
IbPy should work with any GUI framework available to Python. If you have problems integrating with a particular framework, please post a message to the mailing list with the details.

# Thread Models
IbPy plays nice with three different thread models: native Python threads, Qt3 and Qt4 threads. If the package detects a prior import of Qt3 or Qt4, it will select the appropriate thread class for the (internal) EReader instance. The only requirement is that you must import Qt3 or Qt4 first.

    from PyQt4 import QtGui
    from ib.opt import ibConnection  ## this works
    from ib.opt import ibConnection ## wrong thread model selected!
    from qt import *

Other threading models (e.g., GTK) should work normally. If you have problems, please post a message to the mailing list with details.