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

The `plugin.py` file must contain two things: a plugin object, and a function called `setup()` which creates and returns an instance of your plugin object. Optionally, `setup()` may accept one argument, which will be an instance of Cardinal. This is useful if you need access to the Cardinal internals during initialization of your plugin.

Plugins objects should be comprised of two different types of functions (though neither are required to exist within a plugin.) The first type is private functions. These should be prefixed with an underscore, and should only be used for controlling the flow of logic within the plugin.

The second type is command functions. These are the functions that Cardinal will route messages to, when it detects that a command has been called. They should accept four arguments. The first will be an instance of `CardinalBot`. The second is a `re.match()` result with the first group containing the sending user's nick, the second group containing the sending user's ident, and the third group containing the sending user's vhost. The third argument will be the channel the message was sent to (however, if the message was sent in a PM to Cardinal, this will contain the sending user's nick instead.) And finally, the fourth argument will be the full message received.

An example of a function definition for a command is as follows:

```python
def hello(self, cardinal, user, channel, msg):
```

Command functions should also contain a couple attributes. The first is a `commands` attribute, which should be a list of commands that Cardinal should respond to. For example, if Cardinal should respond to ".hello" or "Cardinal: hello", the list should contain the term `hello`. The second is the `help` attribute. This may be either a string, or a list of strings, to be sent when the included `help` command is called, with the command function as its parameter. If the attribute is a list of strings, each string will be sent separately. It is recommended that you use a list of two strings, with one briefly describing the command, and the second providing syntax. An example is below:

```python
hello.commands = ['hello', 'hi']
hello.help = ["Responds to the user with a greeting.",
              "Syntax: .hello [user to greet]"]
```

Note: Square bracket notation should be used for optional parameters, while angled brackets should be used for required parameters.

Lastly, they may contain a `regex` attribute, either as an alternative to a `command` attribute, or in addition to the `command` attribute. If the regex is detected in any received message, the command will be called.

Additionally, a `close()` function may be defined, which will be called whenever the plugin is unloaded (this includes during reloads.)

The default command symbol is `.`. To change this, you must modify the `command_regex` variable in `CardinalBot.py`.

Contributing
------------
If you have found a bug, feel free to submit a patch or simply open an issue on this repository and I will get to it as soon as possible. Be sure to add your name to the CONTRIBUTORS file in a separate commit on the same branch as your modification so that I can give credit where credit is due.

If you have written a plugin that you feel could be useful to other users of Cardinal, open an issue with a link to a Github repository with your plugin in it, and I will consider adding it to the project as a [Git submodule](http://git-scm.com/book/en/Git-Tools-Submodules).

If you simply have a suggestion on how to improve the bot, feel free to open an issue with your suggestion as well!

Cardinal is a public project, and open to anyone who is interested in contributing.
