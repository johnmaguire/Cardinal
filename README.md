Cardinal
========
A modular, Twisted IRC bot.

Instructions
------------
Running Cardinal is as simple as typing `./cardinal.py`. To configure it to connect to your network you may either modify `cardinal.py` or use command line options. Run `./cardinal.py -h` for more information.

To install a plugin, simply import the plugin in `CardinalBot.py` and add it to the `plugins` dictionary.

Plugins
-------
A plugin must contain a `setup()` function. This function should return a list of callable functions which have attributes `regex` and/or `commands`. The function will be called if a message is received in a channel or via PM matching the regex or the command.

Plugin functions should accept four arguments. The first will be an instance of CardinalBot. The second is a re.match result with the first group containing the sending user's nick, the second group containing the sending user's ident, and the third group containing the sending user's vhost. The third argument will be the channel the message was sent to (will contain the user's nickname if it was sent in a PM to Cardinal.) The fourth argument will be the full message received.

The default command symbol is `.`. To change this, you must modify the `command_regex` in `CardinalBot.py`.
