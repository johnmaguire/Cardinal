Cardinal
========
A modular, Twisted IRC bot.

Instructions
------------
To install a plugin, simply import the plugin in CardinalBot.py and add it to the `modules` dictionary.

Plugins
-------
A plugin must contain a setup() function. This function should return a list of callable functions with an attribute `regex`. The function will be called if a message is received in a channel or via PM matching this value.

Plugin functions should accept four arguments. The first will be an instance of CardinalBot. The second is a re.match result with the first group containing the sending user's nick, the second group containing the sending user's ident, and the third group containing the sending user's vhost. The third argument will be the channel the message was sent to (will contain the user's nickname if it was sent in a PM to Cardinal.) The fourth argument will be the full message received.
