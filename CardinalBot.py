# Copyright (c) 2013 John Maguire <john@leftforliving.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation the 
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or 
# sell copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS 
# IN THE SOFTWARE.

import os
import sys
import importlib
import inspect
import re

from twisted.words.protocols import irc
from twisted.internet import protocol

plugins = [
    'ping',
    'urls',
    'weather',
#    'admin',
#    'lastfm',
]

class CardinalBot(irc.IRCClient):
    # Path of executed file
    path = os.path.dirname(os.path.realpath(sys.argv[0]))

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

    def __init__(self):
        # Attempt to load plugins
        self._load_plugins(plugins, True)

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

    def _load_plugins(self, plugins, first_run=False):
        # A dictionary of loaded plugins
        loaded_plugins = self.loaded_plugins

        # A list of plugins that failed to load
        failed_plugins = []

        # Turn this into a list if it isn't one
        if isinstance(plugins, basestring):
            plugins = [plugins]

        for plugin in plugins:
            # Import each plugin with a custom _import_module function.
            try:
                module = self._import_module(loaded_plugins[plugin]['module'] if plugin in loaded_plugins else plugin)
            except Exception, e:
                print >> sys.stderr, "ERROR: Could not load plugin module: %s (%s)" % (plugin, e)
                failed_plugins.append(plugin)

                continue

            # Import each config with the same _import_module function.
            try:
                config = self._import_module(loaded_plugins[plugin]['config'] if plugin in loaded_plugins else plugin, config=True)
            except ImportError:
                config = None
            except Exception, e:
                config = None
                print >> sys.stderr, "WARNING: Could not load plugin config: %s (%s)" % (plugin, e)

            # Create a new instance of the plugin
            try:
                instance = self._create_plugin_instance(module)
            except Exception, e:
                print >> sys.stderr, "ERROR: Could not create plugin instance: %s (%s)" % (plugin, e)
                continue

            # Set module, config, and instance of the plugin
            loaded_plugins[plugin] = {}
            loaded_plugins[plugin]['module'] = module
            loaded_plugins[plugin]['config'] = config
            loaded_plugins[plugin]['instance'] = instance
            loaded_plugins[plugin]['commands'] = self._get_plugin_commands(instance)

            # If we are just starting Cardinal, print a list of loaded plugins.
            if first_run:
                print "Loaded plugin %s" % plugin

        self.loaded_plugins = loaded_plugins

        if len(failed_plugins) > 0:
            return failed_plugins
        else:
            return None

    def _unload_plugins(self, plugins):
        # A list of plugins that weren't loaded in the first place
        nonexistent_plugins = []

        for plugin in plugins:
            if plugin not in self.loaded_plugins:
                nonexistent_plugins.append(plugin)
                continue

            del self.loaded_plugins[plugin]

        if len(nonexistent_plugins) > 0:
            return nonexistent_plugins
        else:
            return None

    # A shorthand version of loaded_plugins['plugin']['config']
    def config(self, plugin):
        return self.loaded_plugins[plugin]['config']

    # This is triggered when we have signed onto the network
    def signedOn(self):
        print "Signed on as %s." % self.nickname
        for channel in self.factory.channels:
            self.join(channel)

    # This is triggered when we have joined a channel
    def joined(self, channel):
        print "Joined %s." % channel

    # This is triggered when we have received a message
    def privmsg(self, user, channel, msg):
        print "(%s)>>> %s" % (channel, msg)

        # Break the user up into usable groups
        user = re.match(self.user_regex, user)

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

    # This is a wrapper command to really quit the server
    def disconnect(self, message=''):
        print "Disconnecting..."
        self.factory.quit = True
        self.quit(message)

    # This is a wrapper command to send messages
    def sendMsg(self, user, message, length=None):
        print "(%s)<<< %s" % (user, message)
        self.msg(user, message, length)

# This interfaces CardinalBot with the Twisted library
class CardinalBotFactory(protocol.ClientFactory):
    quit = False
    protocol = CardinalBot

    def __init__(self, channels, nickname='Cardinal'):
        self.channels = channels
        self.nickname = nickname

    def clientConnectionLost(self, connector, reason):
        if not quit:
            print "Lost connection (%s), reconnecting." % reason
            connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % reason
