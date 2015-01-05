Meet Cardinal.
========
Cardinal is your new best friend and personal assistant on IRC. A modular, Twisted-based Python IRC bot, Cardinal has plenty of common features (such as a calculator, fetching of page titles, etc.) as well as some more interesting ones (integration with Last.fm and YouTube searching.) If you're a developer, it's easy to create your own plugins in a matter of minutes.

Instructions
------------
Running Cardinal is as simple as typing `./cardinal.py`. Before running Cardinal, you should ensure that you have set your network settings in the `cardinal.py` file, or run `./cardinal.py -h` to use command line arguments to set the network and channels you would like Cardinal to connect to.

Before running Cardinal, you should add your nick and vhost to the `plugins/admin/config.py` file in the format `nick@vhost` in order to take advantage of admin-only commands.

What can Cardinal do?
----------------
Out of the box Cardinal can...

* Get the title of URLs in chat
* Search for YouTube videos
* Get the current weather for a given location
* Give users' now playing track on Last.fm and compare Last.fm users
* Send reminder messages
* Act as a calculator and unit/currency converter
* Save "notes" -- effectively turns Cardinal into an info bot
* ... and more!

But Cardinal is still in active development! Features are being added as quickly as they can be thought up and coded. It's also easy to write your own plugins for added functionality!

Writing Plugins
---------------
Writing plugins is simple and quick! Simply create a folder in the `plugins/` directory, add an empty `__init__.py` file, and create a `plugin.py` file to contain your plugin.

The `plugin.py` file must contain two things: a plugin object, and a function called `setup()` which creates and returns an instance of your plugin object. `setup()` may accept zero, one, or two arguments. If one argument is specified, the instance of `CardinalBot` will be passed into it, allowing you to pass it to the plugin instance. If two arguments are specified, the second argument will receive your plugin's config (this should be either `config.json` or `config.yaml` within the plugin directory.)

Plugins objects should be comprised of two different types of methods (though neither are required to exist within a plugin.) Private methods, which should be prefixed with an underscore, which can be used only internally by your plugin, and public methods.

Public methods act as commands for Cardinal. These are the methods that Cardinal will route messages to when it detects that a command has been called. They should accept four arguments. The first argument passed in will be the instance of `CardinalBot`. The second is a `re.match()` return value, with the first group containing the sending user's nick, the second group containing the sending user's ident, and the third group containing the sending user's vhost. The third argument will be the channel the message was sent to (however, if the message was sent in a PM to Cardinal, this will contain the sending user's nick instead. This allows you to send messages to the correct location easily.) And finally, the fourth argument will be the full message received.

An example of a function definition for a command is as follows:

```python
def hello(self, cardinal, user, channel, msg):
```

Command methods should also contain a couple of attributes. The first is a `commands` attribute, which should be a list of commands that Cardinal should respond to. For example, if Cardinal should respond to ".hello" or "Cardinal: hello", the list should contain the term `hello`. The second is the `help` attribute. This may be either a string, or a list of strings, to be sent when the included `help` command is called, with the command function as its parameter. If the attribute is a list of strings, each string will be sent separately. It is recommended that you use a list of two strings, with one briefly describing the command, and the second providing syntax. An example is below:

```python
hello.commands = ['hello', 'hi']
hello.help = ["Responds to the user with a greeting.",
              "Syntax: .hello [user to greet]"]
```

Note: Square bracket notation should be used for optional parameters, while angled brackets (`<>`) should be used for required parameters.

Lastly, they may contain a `regex` attribute, either as an alternative to a `command` attribute, or in addition to the `command` attribute. If the regex is detected in any received message, the command will be called.

Additionally, a `close()` function may be defined at the module level, which will be called whenever the plugin is unloaded (this includes during reloads.)

The default command symbol is `.`. To change this, you must modify the `command_regex` variable in `CardinalBot.py`.

Methods on CardinalBot
----------------------
`CardinalBot` contains a few methods that are useful for plugin developers.

The first, and most important is `sendMsg()`. This takes a parameter `channel` and a parameter `message` and sends the message to the specified channel. Additionally, a `length` parameter may be specified, denoting the length of the message, but this is completely unnecessary and will be taken care of for you if it's not passed in.

The method `disconnect()` allows you to tell Cardinal to disconnect from the network. It can accept a `message` parameter, which, if provided, will specificy a quit message.

Finally, the `config()` method allows you to access the config of a loaded plugin. This should not be called in the constructor of plugins, as `config()` will not work until initial setup is fully completed. It can however be called within other methods of your plugins (such as when responding to a command), to view the config values of other loaded plugins. You can find an example in the `help` plugin, where we look for bot owners, specified in the `admin` plugin's config.

Contributing
------------
If you have found a bug, feel free to submit a patch or simply open an issue on this repository and I will get to it as soon as possible. Be sure to add your name to the CONTRIBUTORS file in a separate commit on the same branch as your modification so that I can give credit where credit is due.

If you have written a plugin that you feel could be useful to other users of Cardinal, open an issue with a link to a Github repository with your plugin in it, and I will consider adding it to the project as a [Git submodule](http://git-scm.com/book/en/Git-Tools-Submodules).

If you simply have a suggestion on how to improve the bot, feel free to open an issue with your suggestion as well!

Cardinal is a public, open-source project, and anyone may contribute.
