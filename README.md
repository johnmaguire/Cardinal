Cardinal
========
A modular, Twisted IRC bot.

Instructions
------------
Running Cardinal is as simple as typing `./cardinal.py`. To configure it to connect to your network you may either modify `cardinal.py` or use command line options. Run `./cardinal.py -h` for more information.

To install a plugin, simply add the plugin name to the `plugins` list in `CardinalBot.py`.

To use the admin plugin, modify `plugins/admin/config.py` to contain your username and vhost in the following format: `nick@vhost`. Finally, uncomment the admin plugin from your `plugins` list in `CardinalBot.py`. 

To use the Last.fm now playing plugin, modify `plugins/lastfm/config.py` to contain your Last.fm API key and then uncomment it from the `plugins` list in `CardinalBot.py`.

What does it do?
----------------
Currently, Cardinal can...

* Get the title of URLs in chat
* Search for YouTube videos
* Get the current weather for a given location
* Give users' now playing track on Last.fm and compare Last.fm users
* Send reminder messages
* ... and more!

But Cardinal is still in active development! Features are being added as quickly as they can be thought up and coded. It's also easy to write your own plugins for added functionality!

Writing Plugins
-------
A plugin must contain a `setup()` function. This function should return an instance of your plugin object. The object should contain functions which will act as commands.

Plugin command functions should accept four arguments. The first will be an instance of `CardinalBot`. The second is a `re.match()` result with the first group containing the sending user's nick, the second group containing the sending user's ident, and the third group containing the sending user's vhost. The third argument will be the channel the message was sent to (will contain the user's nickname if it was sent in a PM to Cardinal.) The fourth argument will be the full message received.

The default command symbol is ".". To change this, you must modify the `command_regex` variable in "CardinalBot.py".
