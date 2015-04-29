# Meet Cardinal.
Cardinal is your new best friend and personal assistant on IRC. A modular, Twisted-based Python IRC bot, Cardinal has plenty of common features (such as a calculator, fetching of page titles, etc.) as well as some more interesting ones (integration with Last.fm and YouTube searching.) If you're a developer, it's easy to create your own plugins in a matter of minutes.

## Basic Usage
Running Cardinal is as simple as typing `./cardinal.py`. Before running Cardinal, you should ensure that you have set your network settings in the `config.json` file, or run `./cardinal.py -h` to use command line arguments to set the network and channels you would like Cardinal to connect to.

Before running Cardinal, you should add your nick and vhost to the `plugins/admin/config.json` file in the format `nick@vhost` in order to take advantage of admin-only commands.

### Installation Note
Make sure you have Python 2.7 installed, and run `pip install -r requirements.txt` to install any Python dependencies.

It is recommended that you install and use Cardinal inside of a [Python virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/). You can do so by running the following commands inside of your cloned repository.

`virtualenv -p /usr/bin/python2.7 .`
`source bin/activate`

In the future, you will just have to remember to call `source bin/activate`.

## What can Cardinal do?
Out of the box Cardinal can...

* Grab the page titles for links
* Search for YouTube videos and link them in chat
* Tell you the weather
* Show who's listening to what with Last.fm integration
* Message you with a time-based reminder
* Act as a calculator and unit/currency converter
* Save "notes" -- effectively turns Cardinal into an info bot
* Grab definitions from Urban Dictionary
* ... and more!

But Cardinal is still in active development! Features are being added as quickly as they can be thought up and coded. It's also easy to write your own plugins for even more functionality.

## Writing Plugins
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

## Methods on CardinalBot
`CardinalBot` contains a few methods that are useful for plugin developers.

The first, and most important is `CardinalBot.sendMsg()`. This takes a parameter `channel` and a parameter `message` and sends the message to the specified channel. Additionally, a `length` parameter may be specified, denoting the length of the message, but this is completely unnecessary and will be taken care of for you if it's not passed in.

The method `CardinalBot.disconnect()` allows you to tell Cardinal to disconnect from the network. It can accept a `message` parameter, which, if provided, will specificy a quit message.

Finally, the `CardinalBot.config()` method allows you to access the config of a loaded plugin. This should not be called in the constructor of plugins, as `CardinalBot.config()` will not work until initial setup is fully completed. It can however be called within other methods of your plugins (such as when responding to a command), to view the config values of other loaded plugins. You can find an example in the `help` plugin, where we look for bot owners, specified in the `admin` plugin's config.

### Event-based Plugins
Cardinal also supports events as of version 2.0. Built-in are the core IRC events:

* `irc.invite` - 2 arguments (inviter, channel)
* `irc.privmsg` - 3 arguments (sender, channel, message)
* `irc.notice` - 3 arguments (sender, channel, message)
* `irc.nick` - 2 arguments (changer, new nick)
* `irc.mode` - 3 arguments(setter, channel, mode)
* `irc.join` - 2 arguments (joiner, channel)
* `irc.part` - 3 arguments (leaver, channel, message)
* `irc.kick` - 4 arguments (kicker, channel, kicked nick, message)
* `irc.quit` - 2 arguments (quitter, message)

Except for "new nick" for the `irc.nick` event and "kicked nick" for the `irc.kick` event, the user arguments are the same as for commands: Three groups returned by `re.match` that contain a user's nick, user identity, and hostname. Also, similarly to commands, event handlers (callbacks triggered when an event fires) all must take an extra first parameter, that is the instance of `CardinalBot`. An event handler for `irc.invite` looks like this:

```python
class InviteJoinPlugin(object):
    def join_channel(self, cardinal, user, channel):
        """Callback for irc.invite that joins a channel"""
        cardinal.join(channel)
```

This would cause Cardinal to join the channel that she was invited to. You should register handlers for events in the `__init__` method of your plugin, and remove handlers you registered in the `close` method of your plugin (called when your plugin is closed by Cardinal.) When registering handlers, you will receive a "callback ID" back from Cardinal. You must hold onto this in order to remove the callback later. For example:

```python
class InviteJoinPlugin(object):
    def __init__(self, cardinal):
        """Register our callback and save the callback ID"""
        self.callback_id = cardinal.event_manager.register_callback("irc.invite", self.join_channel)

    def close(self, cardinal):
        """When the plugin is closed, removes our callback"""
        cardinal.event_manager.remove_callback("irc.invite", self.callback_id)
```

Registering events is easy too. Simply call `EventManager.register()` (accessible from within an event handler or command method as `cardinal.event_manager.register()` with the name of your event, and the number of parameters that will be passed in when you fire the event. Preferably, your event should be prefixed with the name of your plugin, followed by a period. For example `urls.match` for a `urls` plugin that found a matching URL. For example:

```python
class URLsPlugin(object):
    def __init__(self, cardinal):
        """Register our event"""
        cardinal.event_manager.register('urls.match', 1)

    def close(self, cardinal):
        "Remove the event"""
        cardinal.event_manager.remove('urls.match')
```

It is important to remove the event in the `close` method of your plugin. If you don't, and your plugin is reloaded, you will not be able to re-register the event. Once you have your event registered in your plugin. You can call `cardinal.event_manager.fire`, with the first parameter as the name of your event, and the rest of the parameters the ones you want to pass to the event handlers. You may check the boolean return value of `cardinal.plugins.EventManager.fire()` in order to find out whether an event handler did something with your event.

If your event handler is triggered by an event, but for some reason you would like to "refuse" the event (say you are looking for a specific type of URL, and the URL that was provided did not match), you can throw a `cardinal.exceptions.EventRejectedMessage` exception, and the return value of `cardinal.plugins.EventManager.fire()` will not be set to `True`.

## Contributing
If you have found a bug, feel free to submit a patch or simply open an issue on this repository and I will get to it as soon as possible. Be sure to add your name to the CONTRIBUTORS file in a separate commit on the same branch as your modification so that I can give credit where credit is due.

Cardinal is a public, open-source project, licensed under the MIT License. Anyone may contribute.
