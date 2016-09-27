# Synopsis
    from ib.opt import ibConnection, message
    
    def my_account_handler(msg):
        ... do something with account msg ...
    
    def my_tick_handler(msg):
        ... do something with market data msg ...
    
    connection = ibConnection()
    connection.register(my_account_handler, 'UpdateAccountValue')
    connection.register(my_tick_handler, 'TickSize', 'TickPrice')
    connection.connect()
    connection.reqAccountUpdates(...)

# Details
IbPy provides an optional interface that does not require subclassing. This interface lives in the ib.opt package, and provides several conveniences for your use.

To interoperate with this package, first define your handlers. Each handler must take a single parameter, a Message instance. Instances of Message have attributes and values set by the connection object before they're passed to your handler.

After your handlers are defined, you associate them with the connection object via the register method. You pass your handler as the first parameter, and you indicate what message types to send it with parameters that follow it. Message types can be strings, or better, Message classes. Both forms are shown here:

    connection.register(my_account_handler, 'UpdateAccountValue')
    connection.register(my_tick_handler, message.TickPrice, message.TickSize)

You can break the association between your handlers and messages with the unregister method, like so:

    connection.unregister(my_tick_handler, message.TickSize)

In the above example, my_tick_handler will still be called with TickPrice messages.

Connection objects also allow you to associate a handler with all messages generated. The call looks like this:

    connection.registerAll(my_generic_handler)

And of course, there's an unregisterAll method as well:

    connection.unregisterAll(my_generic_handler)

## Attributes
The Connection class exposes the attributes of its connection, so you can write:

    connection.reqIds()

## Logging
The Connection class provides a basic logging facility (via the Python logging module). To activate it, call it like this:

    connection.enableLogging()

To deactivate logging, call the same method with False as the first parameter:

    connection.enableLogging(False)

## Message Objects
Your handlers are passed a single parameter, an instance of the Message class (or one of its subclasses). These instances will have attributes that match the parameter names from the underlying method call. For example, when you're passed a Message instance generated from a TickSize call, the object might look like this:

    msg.tickerId = 4
    msg.field = 3
    msg.size = 100