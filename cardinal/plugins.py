from __future__ import absolute_import, print_function, division

from future import standard_library
standard_library.install_aliases()
from builtins import range
from builtins import object
import os
import re
import string
import logging
import importlib
import inspect
import linecache
import random
import json
from collections import OrderedDict, defaultdict
from copy import copy
from imp import reload

from cardinal.exceptions import (
    CommandNotFoundError,
    ConfigNotFoundError,
    EventAlreadyExistsError,
    EventCallbackError,
    EventDoesNotExistError,
    EventRejectedMessage,
    PluginError,
)

from twisted.internet import defer


class PluginManager(object):
    """Keeps track of, loads, and unloads plugins."""

    COMMAND_REGEX = re.compile(r'\.([A-Za-z0-9_-]+)\s?.*$')
    """Regex for matching standard commands.

    This will check for anything beginning with a period (.) followed by any
    alphanumeric character, then whitespace, then any character(s). This means
    registered commands will be found so long as the registered command is
    alphanumeric (or either _ or -), and any additional arguments will be up to
    the plugin for handling.
    """

    NATURAL_COMMAND_REGEX = r'%s:\s+([A-Za-z0-9_-]+)\s?.*$'
    """Regex for matching natural commands.

    This will check for anything beginning with the bot's nickname, a colon
    (:), whitespace, then an alphanumeric command. This may optionally be the
    end of the message, or there may be whitespace followed by any characters
    (additional arguments) which will be up to the plugin for handling.
    """

    def __init__(self,
                 cardinal,
                 plugins,
                 blacklist,
                 _plugin_module_import_prefix='plugins',
                 _plugin_module_directory_suffix='plugins'):
        """Creates a new instance, optionally with a list of plugins to load

        Keyword arguments:
          cardinal -- An instance of `CardinalBot` to pass to plugins.
          plugins -- A list of plugins to be loaded when instanced.

        Raises:
          TypeError -- When the `plugins` argument is not a list.

        """
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Module name from which plugins are imported. This exists to assist
        # in unit testing.
        self._plugin_module_import_prefix = _plugin_module_import_prefix

        # This is where we'll look for plugins
        self.plugins_directory = os.path.abspath(os.path.join(
            # Get the path to this file's directory
            os.path.dirname(os.path.realpath(os.path.abspath(__file__))),
            # Go up one level
            '..',
            # And add the `plugins/` directory unless overridden
            _plugin_module_directory_suffix
        ))

        # Set default to empty object
        self.plugins = {}

        # Plugin blacklist from persistent config
        self._blacklist = blacklist

        # To prevent circular dependencies, we can't sanity check this. Hope
        # for the best.
        self.cardinal = cardinal

        # Used for iterating PluginManager plugins
        self.iteration_counter = 0

        self.load(plugins)

    def __iter__(self):
        """Part of the iterator protocol, returns iterator object.

        In this case, this will return itself as it keeps track of the iterator
        internally. Before returning itself, the iteration counter will be
        reset to 0.

        Returns:
          PluginManager -- Returns the current instance.

        """
        # Reset the iteration counter
        self.iteration_counter = 0

        return self

    def __next__(self):
        """Part of the iterator protocol, returns the next plugin.

        Returns:
          dict -- Dictionary containing a plugin's data.

        Raises:
          StopIteration -- Raised when there are no plugins left.

        """
        # Make sure we have the dictionary sorted so we return the proper
        # element
        keys = sorted(self.plugins.keys())

        # Increment the counter
        self.iteration_counter += 1

        if self.iteration_counter > len(keys):
            raise StopIteration

        return self.plugins[keys[self.iteration_counter - 1]]

    def _import_module(self, module, suffix='plugin'):
        """Given a plugin name, will import it from its directory or reload it.

        If we are passing in a module, we can safely assume at this point that
        it's a plugin we've already loaded, so we just need to run reload() on
        it. However, if we're loading it fresh then we need to import it out
        of the plugins directory.

        Returns:
          object -- The module that was loaded.

        """
        # Sort of a hack... this helps with debugging, as uncaught exceptions
        # can show the wrong data (line numbers / relevant code) if linecache
        # doesn't get cleared when a module is reloaded. This is Python's
        # internal cache of code files and line numbers.
        linecache.clearcache()

        if inspect.ismodule(module):
            return reload(module)
        elif isinstance(module, str):
            return importlib.import_module('%s.%s.%s' %
                                           (self._plugin_module_import_prefix,
                                            module,
                                            suffix))

    def _create_plugin_instance(self, module, config=None):
        """Creates an instance of the plugin module.

        If the setup() function of the plugin's module takes an argument then
        we will provide the instance of CardinalBot to the plugin. If it takes
        two, we will provide Cardinal, and its config.

        Keyword arguments:
          module -- The module to instantiate.
          config -- A config, if any, belonging to the plugin.

        Returns:
          object -- The instance of the plugin.

        Raises:
          PluginError -- When a plugin's setup function has more than one
            argument.
        """
        if (not hasattr(module, 'setup') or
                not inspect.isfunction(module.setup)):
            raise PluginError("Plugin does not have a setup function")

        # Check whether the setup method on the module accepts an argument. If
        # it does, they are expecting our instance of CardinalBot to be passed
        # in. If not, just call setup. If there is more than one argument
        # accepted, the method is invalid.
        argspec = inspect.getfullargspec(module.setup)
        if len(argspec.args) == 0:
            instance = module.setup()
        elif len(argspec.args) == 1:
            instance = module.setup(self.cardinal)
        elif len(argspec.args) == 2:
            instance = module.setup(self.cardinal, config)
        else:
            raise PluginError("Unknown arguments for setup function")

        return instance

    def _register_plugin_callbacks(self, callbacks):
        """Registers callbacks found in a plugin

        Registers all event callbacks provided by _get_plugin_callbacks with
        EventManager. Callback IDs will be stored in callback_ids so we can
        remove them on unload. It is possible to have multiple methods as
        callbacks for a single event, and to use the same method as a callback
        for multiple events.

        Keyword arguments:
            callbacks - List of callbacks to register.

        Returns:
            dict -- Maps event names to a list of EventManager callback IDs.
        """
        # Initialize variable to hold events callback IDs
        callback_ids = defaultdict(list)

        def rollback():
            for event_name, ids in list(callback_ids.items()):
                for id_ in ids:
                    self.cardinal.event_manager.remove_callback(
                        event_name, id_)

        # Loop through list of dictionaries
        try:
            for callback in callbacks:
                # Loop through all events the callback should be registered to
                for event_name in callback['event_names']:
                    # Get callback ID from register_callback method
                    id_ = self.cardinal.event_manager.register_callback(
                        event_name, callback['method'])

                    # Append to list of callbacks for given event_name
                    callback_ids[event_name].append(id_)
        except Exception:
            rollback()
            raise

        return callback_ids

    def _unregister_plugin_callbacks(self, plugin):
        """Unregisters all events found in a plugin.

        Will remove all callbacks stored in callback_ids from EventManager.

        Keyword arguments:
            plugin - The name of plugin to unregister events for.
        """

        # Reference to plugin
        plugin = self.plugins[plugin]

        # Loop though each event name
        for event_name in list(plugin['callback_ids'].keys()):
            # Loop tough callbacks
            for callback_id in plugin['callback_ids'][event_name]:
                self.cardinal.event_manager.remove_callback(
                    event_name, callback_id)

                # Remove callback ID from registered_events
                plugin['callback_ids'][event_name].remove(callback_id)

    def _close_plugin_instance(self, plugin):
        """Calls the close method on an instance of a plugin.

        If the plugin's module has a close() function, we will check whether
        it expects an instance of CardinalBot or not by checking whether it
        accepts an argument or not. If it does, we will pass in the instance of
        CardinalBot. This method is called just prior to removing the internal
        reference to the plugin's instance.

        Keyword arguments:
          plugin -- The name of the plugin to remove the instance of.

        Raises:
          PluginError -- When a plugin's close function has more than one
            argument.
        """

        instance = self.plugins[plugin]['instance']

        if hasattr(instance, 'close') and inspect.ismethod(instance.close):
            # The plugin has a close method, so we now need to check how
            # many arguments the method has. If it only has one, then the
            # argument must be 'self' and therefore they aren't expecting
            # us to pass in an instance of CardinalBot. If there are two
            # arguments, they expect CardinalBot. Anything else is invalid.
            argspec = inspect.getfullargspec(
                instance.close
            )

            if len(argspec.args) == 1:
                instance.close()
            elif len(argspec.args) == 2:
                instance.close(self.cardinal)
            else:
                raise PluginError("Unknown arguments for close function")

    def _load_plugin_config(self, plugin):
        """Loads a JSON config for a given plugin

        Keyword arguments:
          plugin -- Name of plugin to load config for.

        Raises:
          ConfigNotFoundError -- Raised when expected config isn't found.

        """
        # Initialize variable to hold plugin config
        config = None

        # Attempt to load and parse JSON config file
        file_ = os.path.join(
            self.plugins_directory,
            plugin,
            'config.json'
        )
        try:
            f = open(file_, 'r')
            config = json.load(f, object_pairs_hook=OrderedDict)
            f.close()
        # File did not exist or we can't open it for another reason
        except IOError:
            self.logger.debug(
                "Can't open %s - maybe it doesn't exist?" % file_
            )
        # Thrown by json.load() when the content isn't valid JSON
        except ValueError:
            self.logger.warning(
                "Invalid JSON in %s, skipping it" % file_
            )

        # If neither config was found, raise an exception
        if not config:
            raise ConfigNotFoundError(
                "No config found for plugin: %s" % plugin
            )

        # Return config
        return config

    def _get_plugin_commands(self, instance):
        """Find the commands in a plugin and return them as callables.

        Keyword arguments:
          instance -- An instance of a plugin.

        Returns:
          list -- A list of callable commands.

        """
        commands = []

        # Loop through each method on the instance, checking whether it's a
        # method meant to be interpreted as a command or not.
        for method in dir(instance):
            method = getattr(instance, method)

            if callable(method) and (hasattr(method, 'regex') or
                                     hasattr(method, 'commands')):
                # Since this method has either the 'regex' or the 'commands'
                # attribute assigned, it's registered as a command for
                # Cardinal.
                commands.append(method)

        return commands

    def _get_plugin_callbacks(self, instance):
        """Finds the event callbacks in a plugin and returns them as a list.

        Keyword arguments:
            instane -- An instance of plugin

        Returns:
            list -- A list of dictionaries holding event names and callable
                    methods.
        """
        callbacks = []
        for method in dir(instance):
            method = getattr(instance, method)

            if callable(method) and (hasattr(method, 'events')):
                # Since this method has the 'events' attribute assigned,
                # it is registered as a event for Cardinal
                callbacks.append({
                    'event_names': method.events,
                    'method': method
                })

        return callbacks

    def itercommands(self, channel=None):
        """Simple generator to iterate through all commands of loaded plugins.

        Returns:
          iterator -- Iterator for looping through commands
        """
        # Loop through each plugin we have loaded
        for name, plugin in list(self.plugins.items()):
            if channel is not None and channel in plugin['blacklist']:
                continue

            # Loop through each of the plugins' commands (these are actually
            # class methods with attributes assigned to them, so they are all
            # callable) and yield the command
            for command in plugin['commands']:
                yield command

    def load(self, plugins):
        """Takes either a plugin name or a list of plugins and loads them.

        This involves attempting to import the plugin's module, import the
        plugin's config module, instance the plugin's object, and finding its
        commands and events.

        Keyword arguments:
          plugins -- This can be either a single or list of plugin names.

        Returns:
          list -- A list of failed plugins, or an empty list.

        Raises:
          TypeError -- When the `plugins` argument is not a string or list.

        """
        if isinstance(plugins, str):
            plugins = [plugins]
        if not isinstance(plugins, list):
            raise TypeError(
                "Plugins argument must be a string or list of plugins"
            )

        # List of plugins which failed to load
        failed_plugins = []

        for plugin in plugins:
            # Reload flag so we can update the reload counter if necessary
            self.logger.info("Attempting to load plugin: %s" % plugin)

            # Import each plugin's module with our own hacky function to reload
            # modules that have already been imported previously
            try:
                if plugin in list(self.plugins.keys()):
                    self.logger.info("Already loaded, unloading first: %s" %
                                     plugin)

                    module_to_import = self.plugins[plugin]['module']
                    self.unload(plugin)
                else:
                    module_to_import = plugin

                module = self._import_module(module_to_import)
            except Exception:
                # Probably a syntax error in the plugin, log the exception
                self.logger.exception(
                    "Could not load plugin module: %s" % plugin
                )
                failed_plugins.append(plugin)

                continue

            # Attempt to load the config file for the given plugin.
            config = None
            try:
                config = self._load_plugin_config(plugin)
            except ConfigNotFoundError:
                self.logger.debug(
                    "No config found for plugin: %s" % plugin
                )

            # Instanstiate the plugin
            try:
                instance = self._create_plugin_instance(module, config)
            except Exception:
                self.logger.exception(
                    "Could not instantiate plugin: %s" % plugin
                )
                failed_plugins.append(plugin)

                continue

            commands = self._get_plugin_commands(instance)
            callbacks = self._get_plugin_callbacks(instance)

            try:
                # do this last to ensure the rollback functionality works
                # correctly to remove callbacks if loading fails
                callback_ids = self._register_plugin_callbacks(callbacks)
            except Exception:
                self.logger.exception(
                    "Could not register events for plugin: %s" % plugin
                )

                failed_plugins.append(plugin)

                continue

            self.plugins[plugin] = {
                'name': plugin,
                'module': module,
                'instance': instance,
                'commands': commands,
                'callbacks': callbacks,
                'callback_ids': callback_ids,
                'config': config,
                'blacklist': copy(self._blacklist[plugin]) \
                    if plugin in self._blacklist else \
                    [],
            }

            self.logger.info("Plugin %s successfully loaded" % plugin)

        return failed_plugins

    def unload(self, plugins):
        """Takes either a plugin name or a list of plugins and unloads them.

        Simply validates whether we have loaded a plugin by a given name, and
        if so, clears all the data associated with it.

        Keyword arguments:
          plugins -- This can be either a single or list of plugin names.

        Returns:
          list -- A list of failed plugins, or an empty list.

        Raises:
          TypeError -- When the `plugins` argument is not a string or list.

        """
        # If they passed in a string, convert it to a list
        if isinstance(plugins, str):
            plugins = [plugins]
        if not isinstance(plugins, list):
            raise TypeError("Plugins must be a string or list of plugins")

        # We'll keep track of any plugins we failed to unload (either because
        # we have no record of them being loaded or because the method was
        # invalid.)
        failed_plugins = []

        for plugin in plugins:
            self.logger.info("Attempting to unload plugin: %s" % plugin)

            if plugin not in self.plugins:
                self.logger.warning("Plugin was never loaded: %s" % plugin)
                failed_plugins.append(plugin)
                continue

            self._unregister_plugin_callbacks(plugin)

            try:
                self._close_plugin_instance(plugin)
            except Exception:
                # Log the exception that came from trying to unload the
                # plugin, but don't skip over the plugin. We'll still
                # unload it.
                self.logger.exception(
                    "Didn't close plugin cleanly: %s" % plugin
                )
                failed_plugins.append(plugin)

            # Once all references of the plugin have been removed, Python will
            # eventually do garbage collection. We only opened it in one
            # location, so we'll get rid of that now.
            del self.plugins[plugin]

        return failed_plugins

    def unload_all(self):
        """Unloads all loaded plugins.

        This should theoretically only be called when quitting Cardinal (or
        perhaps during a full reload) and therefore we don't need to really
        pay attention to any failed plugins.

        """
        self.logger.info("Unloading all plugins")
        self.unload([plugin for plugin, data in list(self.plugins.items())])

    def blacklist(self, plugin, channels):
        """Blacklists a plugin from given channels.

        Keyword arguments:
          plugin -- Name of plugin whose blacklist to operate on
          channels -- A list of channels to add to the blacklist

        Returns:
          bool -- False if plugin doesn't exist.
        """
        # If they passed in a string, convert it to a list
        if isinstance(channels, str):
            channels = [channels]
        if not isinstance(channels, list):
            raise TypeError("Plugins must be a string or list of plugins")

        if plugin not in self.plugins:
            return False

        self.plugins[plugin]['blacklist'].extend(channels)

        return True

    def unblacklist(self, plugin, channels):
        """Removes channels from a plugin's blacklist.

        Keyword arguments:
          plugin -- Name of plugin whose blacklist to operate on
          channels -- A list of channels to remove from the blacklist

        Returns:
          list/bool -- False if plugin doesn't exist, list of channels that
            weren't blacklisted in the first place if it does.
        """
        # If they passed in a string, convert it to a list
        if isinstance(channels, str):
            channels = [channels]
        if not isinstance(channels, list):
            raise TypeError("Plugins must be a string or list of plugins")

        if plugin not in self.plugins:
            return False

        not_blacklisted = []

        for channel in channels:
            if channel not in self.plugins[plugin]['blacklist']:
                not_blacklisted.append(channel)
                continue

            self.plugins[plugin]['blacklist'].remove(channel)

        return not_blacklisted

    def get_config(self, plugin):
        """Returns a loaded config for given plugin.

        When a plugin is loaded, if a config is found, it will be stored in
        PluginManager. This method returns a given plugin's config, so it can
        be accessed elsewhere.

        Keyword arguments:
          plugin -- A string containing the name of a plugin.

        Returns:
          dict -- A dictionary containing the config.

        Raises:
          ConfigNotFoundError -- When no config exists for a given plugin name.
        """

        if plugin not in self.plugins:
            raise ConfigNotFoundError("Couldn't find requested plugin config")

        if self.plugins[plugin]['config'] is None:
            raise ConfigNotFoundError("Couldn't find requested plugin config")

        return self.plugins[plugin]['config']

    def call_command(self, user, channel, message):
        """Checks a message to see if it appears to be a command and calls it.

        This is done by checking both the `COMMAND_REGEX` and
        `NATURAL_COMMAND_REGEX` properties on this object. If one or both of
        these tests succeeds, we then check whether any plugins have registered
        a matching command. If both of these tests fail, we will check whether
        any plugins have registered a custom regex expression matching the
        message.

        Keyword arguments:
          user -- A tuple containing a user's nick, ident, and hostname.
          channel -- A string representing where replies should be sent.
          message -- A string containing a message received by CardinalBot.

        Raises:
          CommandNotFoundError -- If the message appeared to be a command but
            no matching plugins are loaded.
        """
        # Keep track of whether we called a command for logging purposes
        called_command = False

        # Perform a regex match of the message to our command regexes, since
        # only one of these can match, and the matching groups are in the same
        # order, we only need to check the second one if the first fails, and
        # we only need to use one variable to track this.
        get_command = re.match(self.COMMAND_REGEX, message)
        if not get_command:
            get_command = re.match(
                self.NATURAL_COMMAND_REGEX % re.escape(self.cardinal.nickname),
                message, flags=re.IGNORECASE)

        # Iterate through all loaded commands
        dl = []
        for command in self.itercommands(channel):
            # Check whether the current command has a regex to match by, and if
            # it does, and the message given to us matches the regex, then call
            # the command.
            if hasattr(command, 'regex') and re.search(command.regex, message):
                dl.append(self._call_command(command, user, channel, message))
                called_command = True
                continue

            # If the message didn't match a typical command regex, then we can
            # skip to the next command without checking whether this one
            # matches the message.
            if not get_command:
                continue

            # Check if the plugin defined any standard commands and whether any
            # of them match the command we found in the message.
            if (hasattr(command, 'commands') and
                    get_command.group(1) in command.commands):
                # Matched this command, so call it.
                dl.append(self._call_command(command, user, channel, message))
                called_command = True
                continue

        # Since standard command regex wasn't found, there's no need to raise
        # an exception - we weren't exactly expecting to find a command anyway.
        # Alternatively, if we called a command, no need to raise an exception.
        if called_command:
            return defer.DeferredList(dl)
        elif not get_command:
            return defer.succeed(None)

        # Since we found something that matched a command regex, yet no plugins
        # that were loaded had a command matching, we can raise an exception.
        raise CommandNotFoundError(
            "Command syntax detected, but no matching command found: %s" %
            message
        )

    def _call_command(self, command, user, channel, message):
        """Calls a command method and treats it as a Deferred.

        Keyword arguments:
          command -- A callable for the command that may return a Deferred.
          user -- A tuple containing a user's nick, ident, and hostname.
          channel -- A string representing where replies should be sent.
          message -- A string containing a message received by CardinalBot.
        """
        args = (self.cardinal, user, channel, message)

        d = defer.maybeDeferred(
            command, *args)

        def errback(failure):
            self.logger.error('Unhandled error: {}'.format(failure))

        d.addErrback(errback)

        return d


class EventManager(object):
    def __init__(self, cardinal):
        """Initializes the logger"""
        self.cardinal = cardinal
        self.logger = logging.getLogger(__name__)

        self.registered_events = defaultdict(dict)
        self.registered_callbacks = defaultdict(dict)

    def register(self, name, required_params):
        """Registers a plugin's event so other events can set callbacks.

        Keyword arguments:
          name -- Name of the event.
          required_params -- Number of parameters a callback must take.

        Raises:
          EventAlreadyExistsError -- If register is attempted for an event name
            already in use.
          TypeError -- If required_params is not a number.
        """
        self.logger.debug("Attempting to register event: %s" % name)

        if name in self.registered_events:
            self.logger.debug("Event already exists: %s" % name)
            raise EventAlreadyExistsError("Event already exists: %s" % name)

        if not isinstance(required_params, (int, int)):
            self.logger.debug("Invalid required params: %s" % name)
            raise TypeError("Required params must be an integer")

        self.registered_events[name] = required_params
        if name not in self.registered_callbacks:
            self.registered_callbacks[name] = {}

        self.logger.info("Registered event: %s" % name)

    def remove(self, name):
        """Removes a registered event."""
        self.logger.debug("Attempting to unregister event: %s" % name)

        if name not in self.registered_events:
            self.logger.debug("Event does not exist: %s" % name)
            raise EventDoesNotExistError(
                "Can't remove nonexistent event: %s" % name
            )

        del self.registered_events[name]
        del self.registered_callbacks[name]

        self.logger.info("Removed event: %s" % name)

    def register_callback(self, event_name, callback):
        """Registers a callback to be called when an event fires.

        Keyword arguments:
          event_name -- Event name to bind callback to.
          callback -- Callable to bind.

        Raises:
          EventCallbackError -- If an invalid callback is passed in.
        """
        self.logger.debug(
            "Attempting to register callback for event: %s" % event_name
        )

        if not callable(callback):
            self.logger.debug("Invalid callback for event: %s" % event_name)
            raise EventCallbackError(
                "Can't register callback that isn't callable"
            )

        argspec = inspect.getfullargspec(callback)
        num_func_args = len(argspec.args)

        # If no event is registered, we will still register the callback but
        # we can't sanity check it since the event hasn't been registered yet
        if event_name not in self.registered_events:
            if num_func_args < 1:
                raise EventCallbackError(
                    "Callback must take at least one argument (cardinal)")

            return self._add_callback(event_name, callback)

        # Add one to needed args to account for CardinalBot being passed in
        num_needed_args = self.registered_events[event_name] + 1

        # If it's a method, it'll have an arbitrary "self" argument we don't
        # want to include in our param count
        if inspect.ismethod(callback):
            num_func_args -= 1

        if (num_func_args != num_needed_args and
                not argspec.varargs):
            self.logger.debug("Invalid callback for event: %s" % event_name)
            raise EventCallbackError(
                "Can't register callback with wrong number of arguments "
                "(%d needed, %d accepted)" %
                (num_needed_args, num_func_args)
            )

        return self._add_callback(event_name, callback)

    def remove_callback(self, event_name, callback_id):
        """Removes a callback with a given ID from an event's callback list.

        Keyword arguments:
          event_name -- Event name to remove the callback from.
          callback_id -- The ID generated when the callback was added.
        """
        self.logger.debug(
            "Removing callback %s from callback list for event: %s" %
            (callback_id, event_name)
        )

        if event_name not in self.registered_callbacks:
            self.logger.debug(
                "Callback %s: Event has no callback list" % callback_id
            )
            return

        if callback_id not in self.registered_callbacks[event_name]:
            self.logger.debug(
                "Callback %s: Callback does not exist in callback list" %
                callback_id
            )
            return

        del self.registered_callbacks[event_name][callback_id]

        self.logger.info("Removed callback %s for event: %s",
                         callback_id, event_name)

    def fire(self, name, *params):
        """Calls all callbacks with given event name.

        Keyword arguments:
          name -- Event name to fire.
          params -- Params to pass to callbacks.

        Raises:
          EventDoesNotExistError -- If fire is called a nonexistent event.

        Returns:
          boolean -- Whether a callback (or multiple) was called successfully.
        """
        self.logger.debug("Attempting to fire event: %s" % name)

        if name not in self.registered_events:
            self.logger.debug("Event does not exist: %s" % name)
            raise EventDoesNotExistError(
                "Can't call an event that does not exist: %s" % name
            )

        callbacks = self.registered_callbacks[name]
        self.logger.debug(
            "Calling %d callbacks for event: %s" %
            (len(callbacks), name)
        )

        cb_deferreds = []
        for callback_id, callback in callbacks.items():
            d = defer.maybeDeferred(
                callback, self.cardinal, *params)

            # It is necessary to pass callback_id in to this function in order
            # to make sure it doesn't change when the loop iterates
            def success(_result, callback_id=callback_id):
                self.logger.debug(
                    "Callback {} accepted event '{}'"
                    .format(callback_id, name)
                )

                return True
            d.addCallback(success)

            # It is necessary to pass callback_id in to this function in order
            # to make sure it doesn't change when the loop iterates
            def eventRejectedErrback(failure, callback_id=callback_id):
                # If this exception is received, the plugin told us not to set
                # the called flag true, so we can just log it and continue on.
                # This might happen if a plugin realizes the event does not
                # apply to it and wants the original caller to handle it
                # normally.
                failure.trap(EventRejectedMessage)

                self.logger.debug(
                    "Callback {} rejected event '{}'"
                    .format(callback_id, name)
                )

                return False
            d.addErrback(eventRejectedErrback)

            # It is necessary to pass callback_id in to this function in order
            # to make sure it doesn't change when the loop iterates
            def errback(failure, callback_id=callback_id):
                self.logger.error(
                    "Unhandled error during callback {} for event '{}': {}"
                    .format(callback_id, name, failure)
                )

                return False
            d.addErrback(errback)

            cb_deferreds.append(d)

        dl = defer.DeferredList(cb_deferreds)
        dl.addCallback(self._reduce_callback_accepted_statuses)
        return dl

    @staticmethod
    def _reduce_callback_accepted_statuses(results):
        """Returns True if an event callback accepted the event.

        This is a callback added to a DeferredList representing each of the
        event callback Deferreds. If any one of them accepted the event, return
        True back to the caller that fired the event.
        """
        for res in results:
            success, result = res
            if success and result is True:
                return True

        return False

    def _add_callback(self, event_name, callback):
        """Adds a callback to the event's callback list and returns an ID.

        Keyword arguments:
          event_name -- Event name to add the callback to.
          callback -- The callback to add.

        Returns:
          string -- A callback ID to reference the callback with for removal.
        """
        callback_id = self._generate_id()
        while (event_name in self.registered_callbacks and
                callback_id in self.registered_callbacks[event_name]):
            callback_id = self._generate_id()

        self.registered_callbacks[event_name][callback_id] = callback
        self.logger.info(
            "Registered callback %s for event: %s" %
            (callback_id, event_name)
        )

        return callback_id

    def _generate_id(size=6, chars=string.ascii_uppercase + string.digits):
        """
        Thank you StackOverflow: http://stackoverflow.com/a/2257449/242129

        Generates a random, 6 character string of letters and numbers (by
        default.)
        """
        return ''.join(random.choice(chars) for _ in range(6))
