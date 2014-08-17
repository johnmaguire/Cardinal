import os
import sys
import time
import signal
import importlib
import linecache
import inspect
import re
from datetime import datetime

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor

from plugins import PluginManager

class CardinalBot(irc.IRCClient):
    # Path of executed file
    path = os.path.dirname(os.path.realpath(sys.argv[0]))

    # The current connected network (e.g. 'irc.darchoods.net')
    network = None

    # Get the current nickname from the factory
    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    # This is a regex to split the user nick, ident, and hostname
    user_regex = re.compile(r'^(.*?)!(.*?)@(.*?)$')

    # This is a regex to get the current command
    command_regex = re.compile(r'\.(([A-Za-z0-9_-]+)\w?.*$)')

    # This is a regex to get the current natural command
    natural_command_regex = r'%s:\s+((.+?)(\s(.*)|$))'

    # This dictionary will contain a list of loaded plugins
    loaded_plugins = {}

    # This dictionary will contain all the configuration files
    config = {}

    # Some meta info, keeping track of the uptime of the bot, the boot time
    # (when the first instance of CardinalBot was brought online), and the
    # number of reloads performed.
    uptime  = None
    booted  = None
    reloads = 0

    def _import_module(self, module, config=False):
        if inspect.ismodule(module):
            return reload(module)
        elif isinstance(module, basestring):
            return importlib.import_module('plugins.%s.%s' % (module, 'config' if config else 'plugin'))

    def _create_plugin_instance(self, module):
        argspec = inspect.getargspec(module.setup)
        if len(argspec.args) > 0:
            instance = module.setup(self)
        else:
            instance = module.setup()

        return instance

    def _get_plugin_commands(self, instance):
        # Compile a list of all commands in the plugin
        commands = []
        for method in dir(instance):
            method = getattr(instance, method)
            if callable(method) and (hasattr(method, 'regex') or hasattr(method, 'commands')):
                commands.append(method)

        return commands

    def _get_plugin_events(self, instance):
        # Compile a list of all events in the plugin
        events = []
        for method in dir(instance):
            method = getattr(instance, method)
            if callable(method) and (hasattr(method, 'on_join') or hasattr(method, 'on_part') or
                                     hasattr(method, 'on_quit') or hasattr(method, 'on_kick') or
                                     hasattr(method, 'on_action') or hasattr(method, 'on_topic') or
                                     hasattr(method, 'on_nick') or hasattr(method, 'on_invite')):
                events.append(method)

        return events

    def _load_plugins(self, plugins, first_run=False):
        # A dictionary of loaded plugins
        loaded_plugins = {}

        # A list of plugins that failed to load
        failed_plugins = []

        # Turn this into a list if it isn't one
        if isinstance(plugins, basestring):
            plugins = [plugins]

        linecache.clearcache()

        for plugin in plugins:
            loaded_plugins[plugin] = {}

            # Import each plugin with a custom _import_module function.
            try:
                module = self._import_module(self.loaded_plugins[plugin]['module'] if plugin in self.loaded_plugins else plugin)
            except Exception, e:
                print >> sys.stderr, "ERROR: Could not load plugin module: %s (%s)" % (plugin, e)
                failed_plugins.append(plugin)

                continue

            # Import each config with the same _import_module function.
            try:
                self.config[plugin] = self._import_module(self.config[plugin] if plugin in self.config else plugin, config=True)
            except ImportError:
                self.config[plugin] = None
            except Exception, e:
                self.config[plugin] = None
                print >> sys.stderr, "WARNING: Could not load plugin config: %s (%s)" % (plugin, e)

            # Create a new instance of the plugin
            try:
                instance = self._create_plugin_instance(module)
            except Exception, e:
                print >> sys.stderr, "ERROR: Could not create plugin instance: %s (%s)" % (plugin, e)
                failed_plugins.append(plugin)

                continue

            commands = self._get_plugin_commands(instance)
            events   = self._get_plugin_events(instance)

            # Set module, commands, and instance of the plugin
            loaded_plugins[plugin]['module'] = module
            loaded_plugins[plugin]['instance'] = instance
            loaded_plugins[plugin]['commands'] = commands
            loaded_plugins[plugin]['events'] = events

            if plugin in self.loaded_plugins:
                self._unload_plugins(plugin)
            self.loaded_plugins[plugin] = loaded_plugins[plugin]

            # If we are just starting Cardinal, print a list of loaded plugins
            if first_run:
                print "Loaded plugin %s" % plugin

        # If this is a reload, add to the count
        if not first_run:
                self.reloads += 1

        if len(failed_plugins) > 0:
            return failed_plugins
        else:
            return None

    def _unload_plugins(self, plugins):
        # A list of plugins that weren't loaded in the first place
        nonexistent_plugins = []

        # Turn this into a list if it isn't one
        if isinstance(plugins, basestring):
            plugins = [plugins]

        for plugin in plugins:
            if plugin not in self.loaded_plugins:
                nonexistent_plugins.append(plugin)
                continue

            if (hasattr(self.loaded_plugins[plugin]['instance'], 'close') and
                inspect.ismethod(self.loaded_plugins[plugin]['instance'].close)):
                argspec = inspect.getargspec(self.loaded_plugins[plugin]['instance'].close)
                if len(argspec.args) > 1:
                    self.loaded_plugins[plugin]['instance'].close(self)
                else:
                    self.loaded_plugins[plugin]['instance'].close()

            del self.loaded_plugins[plugin]

        if len(nonexistent_plugins) > 0:
            return nonexistent_plugins
        else:
            return None

    # This is triggered when we have signed onto the network
    def signedOn(self):
        print "Signed on as %s." % self.nickname

        # Give the factory access to the bot
        self.factory.cardinal = self

        # Set the currently connected network
        self.network = self.factory.network

        # Attempt to identify with NickServ, if a password was given
        if self.factory.password:
            print "Attempting to identify with NickServ."
            self.msg("NickServ", "IDENTIFY %s" % (self.factory.password,))

        # Attempt to load plugins
        self._load_plugins(self.factory.plugins, True)

        # Attempt to join channels
        for channel in self.factory.channels:
            self.join(channel)

        # Set the uptime and boot time from the factory
        self.uptime = datetime.now()
        self.booted = self.factory.booted

    # This is triggered when we have joined a channel
    def joined(self, channel):
        print "Joined %s." % channel

    # This is triggered when we have received a message
    def privmsg(self, user, channel, msg):
        # Break the user up into usable groups
        user = re.match(self.user_regex, user)

        # Print message to terminal
        print "(%s)==>(%s) %s" % (user.group(1), channel, msg)

        # Change the channel to something we can reply to
        if channel == self.nickname:
            channel = user.group(1)

        # Check if this was a command
        get_command = re.match(self.command_regex, msg)
        get_natural_command = re.match(self.natural_command_regex % self.nickname, msg, flags=re.IGNORECASE)

        # Loop through each loaded module
        for name, module in self.loaded_plugins.items():
            # Loop through each registered command of the module
            for command in module['commands']:
                # Check whether this matches the regex of the command
                if hasattr(command, 'regex') and re.search(command.regex, msg):
                    command(self, user, channel, msg)
                # Check whether this matches .command syntax
                elif (get_command and hasattr(command, 'commands') and
                      get_command.group(2) in command.commands):
                    command(self, user, channel, get_command.group(1))
                # Check whether this matches Cardinal: command syntax
                elif (get_natural_command and hasattr(command, 'commands') and
                      get_natural_command.group(2) in command.commands):
                    command(self, user, channel, get_natural_command.group(1))

    # This is triggered when a user joins a channel we are on.
    def userJoined(self, nick, channel):
        # Print message to terminal
        print "%s has joined the channel %s." % (nick, channel)

        # Loop through each module to pass this event off to any event which
        # is listening for it.
        for name, module in self.loaded_plugins.items():
            # Loop through each registered event of the module
            for event in module['events']:
                if hasattr(event, 'on_join') and event.on_join:
                    event(self, nick, channel)

    # This is triggered when a user parts a channel we are on.
    def userLeft(self, nick, channel):
        # Print message to terminal
        print "%s parted the channel %s." % (nick, channel)

        # Loop through each module to pass this event off to any event which
        # is listening for it.
        for name, module in self.loaded_plugins.items():
            # Loop through each registered event of the module
            for event in module['events']:
                if hasattr(event, 'on_part') and event.on_part:
                    event(self, nick, channel)

    # This occurs when a user in a channel we are on quits the server.
    def userQuit(self, nick, quitMessage):
        # Print message to terminal
        print "%s has quit (%s)." % (nick, quitMessage)

        # Loop through each module to pass this event off to any event which
        # is listening for it.
        for name, module in self.loaded_plugins.items():
            # Loop through each registered event of the module
            for event in module['events']:
                if hasattr(event, 'on_quit') and event.on_quit:
                    event(self, nick, quitMessage)

    # This occurs when a user is kicked from a channel we are on.
    def userKicked(self, kicked, channel, kicker, message):
        # Print message to terminal
        print "%s has been kicked from %s by %s (Reason: %s)." % (kicked, channel, kicker, message)

        # Loop through each module to pass this event off to any event which
        # is listening for it.
        for name, module in self.loaded_plugins.items():
            # Loop through each registered event of the module
            for event in module['events']:
                if hasattr(event, 'on_kick') and event.on_kick:
                    event(self, kicked, channel, kicker, message)

    # This occurs when a channel uses /me on a channel we are on.
    def action(self, user, channel, data):
        # Break the user up into usable groups
        user = re.match(self.user_regex, user)

        # Print message to terminal
        print "(%s) *** %s %s." % (channel, user.group(1), data)

        # Loop through each module to pass this event off to any event which
        # is listening for it.
        for name, module in self.loaded_plugins.items():
            # Loop through each registered event of the module
            for event in module['events']:
                if hasattr(event, 'on_action') and event.on_action:
                    event(self, user, channel, data)

    # This occurs when a user updates a topic on a channel we are on.
    def topicUpdated(self, nick, channel, newTopic):
        # Print message to terminal
        print "(%s) %s has updated the topic: %s" % (channel, nick, newTopic)

        # Loop through each module to pass this event off to any event which
        # is listening for it.
        for name, module in self.loaded_plugins.items():
            # Loop through each registered event of the module
            for event in module['events']:
                if hasattr(event, 'on_topic') and event.on_topic:
                    event(self, nick, channel, newTopic)

    # This occurs when a user changes their nick in a channel we are on.
    def userRenamed(self, oldname, newname):
        # Print message to terminal
        print "%s is now known as %s." % (oldname, newname)

        # Loop through each module to pass this event off to any event which
        # is listening for it.
        for name, module in self.loaded_plugins.items():
            # Loop through each registered event of the module
            for event in module['events']:
                if hasattr(event, 'on_nick') and event.on_nick:
                    event(self, oldname, newname)

    def irc_unknown(self, prefix, command, params):
        if command == "INVITE":
            nick = params[0]
            channel = params[1]

            for name, module in self.loaded_plugins.items():
                for event in module['events']:
                    if hasattr(event, 'on_invite') and event.on_invite:
                        event(self, nick, channel)

    # This is a wrapper command to really quit the server
    def disconnect(self, message=''):
        self._unload_plugins([plugin for plugin, data in self.loaded_plugins.items()])
        print "Disconnecting..."
        self.factory.disconnect = True
        self.quit(message)

    # This is a wrapper command to send messages
    def sendMsg(self, user, message, length=None):
        print "(%s)<==(%s) %s" % (user, self.nickname, message)
        self.msg(user, message, length)

# This interfaces CardinalBot with the Twisted library
class CardinalBotFactory(protocol.ClientFactory):
    protocol = CardinalBot

    # Whether disconnect.quit() was called.
    disconnect = False

    # The network Cardinal has connected to
    network = None

    # The nickname Cardinal has connected as
    nickname = None

    # The password for Cardinal to identify with, if any
    password = None

    # List of channels for CardinalBot to join
    channels = []

    # List of plugins to start CardinalBot with
    plugins = []

    # The instance of CardinalBot, which will be set by CardinalBot
    cardinal = None

    # The minimum time to wait before attempting to reconnect from an
    # unexpected disconnection (in seconds)
    minimum_reconnection_wait = 10

    # The maximum amount of time to wait before attempting to reconnect from an
    # unexpected disconnection (in seconds)
    maximum_reconnection_wait = 3600

    # The amount of time we waited before attempting to reconnect last
    last_reconnection_wait = None

    # The time the first instance of CardinalBot was brought online
    booted = None

    def __init__(self, network, channels, nickname='Cardinal', password=None, plugins=[]):
        self.network = network.lower()
        self.password = password
        self.channels = channels
        self.nickname = nickname
        self.plugins = plugins

        signal.signal(signal.SIGINT, self._sigint)

        self.booted = datetime.now()

    def _sigint(self, signal, frame):
        self.disconnect = True
        if self.cardinal:
            self.cardinal.quit('Received SIGINT.')

    def clientConnectionLost(self, connector, reason):
        # This flag tells us whether Cardinal was supposed to disconnect or not
        if not self.disconnect:
            # Reset the last reconnection wait time since this is the first
            # time we've disconnected since a successful connection
            self.last_reconnection_wait = self.minimum_reconnection_wait

            print "Lost connection (%s), reconnecting in %d seconds." % (reason, self.minimum_reconnection_wait)
            time.sleep(self.minimum_reconnection_wait)

            connector.connect()
        else:
            print "Lost connection (%s), quitting." % reason
            reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        # If we disconnected on our first connection attempt, then we don't
        # need to calculate a wait time, we can just use the minimum time
        if not self.last_reconnection_wait:
            wait_time = self.minimum_reconnection_wait
        else:
            # We'll attempt to reconnect after waiting twice as long as the
            # last time we waited, unless it exceeds the maximum wait time, in
            # which case we'll wait that long instead
            wait_time = self.last_reconnection_wait * 2
            if wait_time > self.maximum_reconnection_wait:
                wait_time = self.maximum_reconnection_wait
       
        # Set the last reconnection wait time so we can double it next time
        self.last_reconnection_wait = wait_time

        print "Could not connect (%s), retrying in %d seconds" % (reason, wait_time)
        time.sleep(wait_time)

        connector.connect()
