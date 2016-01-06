import os
import sys
import re
import string
import logging
import importlib
import inspect
import linecache
import random
import json
import yaml

from cardinal.exceptions import (
    AmbiguousConfigError,
    CommandNotFoundError,
    ConfigNotFoundError,
    EventAlreadyExistsError,
    EventCallbackError,
    EventDoesNotExistError,
    EventRejectedMessage,
    PluginError,
)


class PluginManager(object):
    """Keeps track of, loads, and unloads plugins."""

    logger = None
    """Logging object for PluginManager"""

    iteration_counter = 0
    """Holds our current iteration point"""

    cardinal = None
    """Holds an instance of `CardinalBot`"""

    plugins = None
    """List of loaded plugins"""

    command_regex = re.compile(r'\.(([A-Za-z0-9_-]+)\s?.*$)')
    """Regex for matching standard commands.

    This will check for anything beginning with a period (.) followed by any
    alphanumeric character, then whitespace, then any character(s). This means
    registered commands will be found so long as the registered command is
    alphanumeric (or either _ or -), and any additional arguments will be up to
    the plugin for handling.
    """

    natural_command_regex = r'%s:\s+(([A-Za-z0-9_-]+?)(\s(.*)|$))'
    """Regex for matching natural commands.

    This will check for anything beginning with the bot's nickname, a colon
    (:), whitespace, then an alphanumeric command. This may optionally be the
    end of the message, or there may be whitespace followed by any characters
    (additional arguments) which will be up to the plugin for handling.
    """

    def __init__(self, cardinal, plugins=None):
        """Creates a new instance, optionally with a list of plugins to load

        Keyword arguments:
          cardinal -- An instance of `CardinalBot` to pass to plugins.
          plugins -- A list of plugins to be loaded when instanced.

        Raises:
          TypeError -- When the `plugins` argument is not a list.

        """
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Set default to empty object
        self.plugins = {}

        # To prevent circular dependencies, we can't sanity check this. Hope
        # for the best.
        self.cardinal = cardinal

        # Make sure we operate on a list
        if plugins is not None and not isinstance(plugins, list):
            raise TypeError("Plugins argument must be a list")
        elif plugins is None:
            return

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

    def next(self):
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

    def _import_module(self, module, type='plugin'):
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
        elif isinstance(module, basestring):
            return importlib.import_module('plugins.%s.%s' % (module, type))

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
        argspec = inspect.getargspec(module.setup)
        if len(argspec.args) == 0:
            instance = module.setup()
        elif len(argspec.args) == 1:
            instance = module.setup(self.cardinal)
        elif len(argspec.args) == 2:
            instance = module.setup(self.cardinal, config)
        else:
            raise PluginError("Unknown arguments for setup function")

        return instance

    def _register_plugin_events(self, events):
        """Registers events found in plugin

        Will get all the events provided by _get_plugin_events though EventManager.
        Callback IDs will be stored in registered_events so we can remove them on unload.
        It is possible to have multiple methods as callback for single event.

        Keyword arguments:
            events - list of events to register

        """

        # Initialize variable to hold events callback IDs
        registered_events = {}

        # Loop though list of tuples
        for event in events:
            #Loop tought event names for each callback
            for event_name in event[0]:
                # Get callback ID from register_callback method
                callback_id = self.cardinal.event_manager.register_callback(event_name, event[1])

                # Append to list of callbacks for given event_name
                if registered_events.has_key(event_name):
                    registered_events[event_name].append(callback_id)
                else:
                    registered_events[event_name] = []
                    registered_events[event_name].append(callback_id)

        return registered_events

    def _unregister_plugin_events(self, plugin):
        """Unregister events found in plugin

        Will remove all events stored in registered_events though EventManager.

        Keyword arguments:
            plugin - The name of plugin to unregister events for

        """

        # Reference to plugin
        plugin = self.plugins[plugin]

        # Loop though each event name
        for event_name in plugin['registered_events'].keys():
            # Loop tough callbacks
            for callback_id in plugin['registered_events'][event_name]:
                self.cardinal.event_manager.remove_callback(event_name, callback_id)
                # Remove callback ID from registered_events
                plugin['registered_events'][event_name].remove(callback_id)

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
            argspec = inspect.getargspec(
                instance.close
            )

            if len(argspec.args) == 1:
                instance.close()
            elif len(argspec.args) == 2:
                instance.close(self.cardinal)
            else:
                raise PluginError("Unknown arguments for close function")

    def _load_plugin_config(self, plugin):
        """Loads a JSON or YAML config for a given plugin

        Keyword arguments:
          plugin -- Name of plugin to load config for.

        Raises:
          AmbiguousConfigError -- Raised when two configs exist for plugin.
          ConfigNotFoundError -- Raised when expected config isn't found.

        """
        # Initialize variable to hold plugin config
        json_config = False
        yaml_config = False

        # Attempt to load and parse JSON config file
        file = os.path.join(
            os.path.dirname(os.path.realpath(sys.argv[0])),
            'plugins',
            plugin,
            'config.json'
        )
        try:
            f = open(file, 'r')
            json_config = json.load(f)
            f.close()
        # File did not exist or we can't open it for another reason
        except IOError:
            self.logger.debug(
                "Can't open %s - maybe it doesn't exist?" % file
            )
        # Thrown by json.load() when the content isn't valid JSON
        except ValueError:
            self.logger.warning(
                "Invalid JSON in %s, skipping it" % file
            )

        # Attempt to load and parse YAML config file
        file = os.path.join(
            os.path.dirname(os.path.realpath(sys.argv[0])),
            'plugins',
            plugin,
            'config.yaml'
        )
        try:
            f = open(file, 'r')
            yaml_config = yaml.load(f)
            f.close()
        except IOError:
            self.logger.debug(
                "Can't open %s - maybe it doesn't exist?" % file
            )
        except ValueError:
            self.logger.warning(
                "Invalid YAML in %s, skipping it" % file
            )
        # Loaded YAML successfully
        else:
            # If we already loaded JSON, this is a problem because we won't
            # know which config to use.
            if json_config:
                raise AmbiguousConfigError(
                    "Found both a JSON and YAML config for plugin"
                )

            # No JSON config, found YAML config, return it
            return yaml_config

        # If neither config was found, raise an exception
        if not yaml_config and not json_config:
            raise ConfigNotFoundError(
                "No config found for plugin: %s" % plugin
            )

        # Return JSON config, since YAML config wasn't found
        return json_config

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

    def _get_plugin_events(self, instance):
        """Find the events in a plugin and return them as callables

        Keyword arguments:
            instane -- An instance of plugin

        Returns:
            list -- A list of tuples holding event names and callable commands.

        """
        events = []
        for method in dir(instance):
            method = getattr(instance, method)

            if callable(method) and (hasattr(method, 'events')):
                # Since this method has the 'events' attribute assigned,
                # it is registered as a event for Cardinal
                events.append((method.events, method))

        return events

    def itercommands(self, channel=None):
        """Simple generator to iterate through all commands of loaded plugins.

        Returns:
          iterator -- Iterator for looping through commands
        """
        # Loop through each plugin we have loaded
        for name, plugin in self.plugins.items():
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
        # If they passed in a string, convert it to a list (and encode the
        # name as UTF-8.)
        if isinstance(plugins, basestring):
            plugins = [plugins.encode('utf-8')]
        if not isinstance(plugins, list):
            raise TypeError(
                "Plugins argument must be a string or list of plugins"
            )

        # We'll keep track of plugins we failed to load (either because we)
        failed_plugins = []

        for plugin in plugins:
            # Reload flag so we can update the reload counter if necessary
            reload_flag = False

            self.logger.info("Attempting to load plugin: %s" % plugin)

            # Import each plugin's module with our own hacky function to reload
            # modules that have already been imported previously
            try:
                if plugin in self.plugins.keys():
                    self.logger.info("Already loaded, reloading: %s" % plugin)
                    reload_flag = True

                    try:
                        self._close_plugin_instance(plugin)
                    except Exception:
                        self.logger.exception(
                            "Didn't close plugin cleanly: %s" % plugin
                        )
                    module_to_import = self.plugins[plugin]['module']
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
            except AmbiguousConfigError:
                # If two configs exist for the plugin, bail on loading
                self.logger.exception("Could not load plugin: %s" % plugin)
                failed_plugins.append(plugin)

                continue
            except ConfigNotFoundError:
                self.logger.info(
                    "No config found for plugin: %s" % plugin
                )

            # Instance the plugin
            try:
                instance = self._create_plugin_instance(module, config)
            except Exception:
                self.logger.exception(
                    "Could not instantiate plugin: %s" % plugin
                )
                failed_plugins.append(plugin)

                continue

            commands = self._get_plugin_commands(instance)
            events = self._get_plugin_events(instance)

            try:
                registered_events = self._register_plugin_events(events)
            except Exception:
                self.logger.exception(
                    "Could not register events for plugin: %s" % plugin
                )
                failed_plugins.append(plugin)

                continue

            if plugin in self.plugins:
                self.unload(plugin)

            self.plugins[plugin] = {
                'name': plugin,
                'module': module,
                'instance': instance,
                'commands': commands,
                'events': events,
                'registered_events': registered_events,
                'config': config,
                'blacklist': [],
            }

            if reload_flag:
                self.cardinal.reloads += 1

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
        # If they passed in a string, convert it to a list (and encode the
        # name as UTF-8.)
        if isinstance(plugins, basestring):
            plugins = [plugins.encode('utf-8')]
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

            try:
                self._unregister_plugin_events(plugin)
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
        self.unload([plugin for plugin, data in self.plugins.items()])

    def blacklist(self, plugin, channels):
        """Blacklists a plugin from given channels.

        Keyword arguments:
          plugin -- Name of plugin whose blacklist to operate on
          channels -- A list of channels to add to the blacklist

        Returns:
          bool -- False if plugin doesn't exist.
        """
        # If they passed in a string, convert it to a list (and encode the
        # name as UTF-8.)
        if isinstance(channels, basestring):
            channels = [channels.encode('utf-8')]
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
        # If they passed in a string, convert it to a list (and encode the
        # name as UTF-8.)
        if isinstance(channels, basestring):
            channels = [channels.encode('utf-8')]
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

        This is done by checking both the `command_regex` and
        `natural_command_regex` properties on this object. If one or both of
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
        get_command = re.match(self.command_regex, message)
        if not get_command:
            get_command = re.match(
                self.natural_command_regex % self.cardinal.nickname, message,
                flags=re.IGNORECASE
            )

        # Iterate through all loaded commands
        for command in self.itercommands(channel):
            # Check whether the current command has a regex to match by, and if
            # it does, and the message given to us matches the regex, then call
            # the command.
            if hasattr(command, 'regex') and re.search(command.regex, message):
                command(self.cardinal, user, channel, message)
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
                    get_command.group(2) in command.commands):
                # Matched this command, so call it.
                called_command = True
                command(self.cardinal, user, channel, message)
                continue

        # Since standard command regex wasn't found, there's no need to raise
        # an exception - we weren't exactly expecting to find a command anyway.
        # Alternatively, if we called a command, no need to raise an exception.
        if not get_command or called_command:
            return

        # Since we found something that matched a command regex, yet no plugins
        # that were loaded had a command matching, we can raise an exception.
        raise CommandNotFoundError(
            "Command syntax detected, but no matching command found: %s" %
            message
        )


class EventManager(object):
    cardinal = None
    """Instance of CardinalBot"""

    registered_events = None
    """Contains all the registered events"""

    registered_callbacks = None
    """Contains all the registered callbacks"""

    def __init__(self, cardinal):
        """Initializes the logger"""
        self.cardinal = cardinal
        self.logger = logging.getLogger(__name__)

        self.registered_events = {}
        self.registered_callbacks = {}

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

        if not isinstance(required_params, (int, long)):
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

        # If no event is registered, we will still register the callback but
        # we can't sanity check it since the event hasn't been registered yet
        if event_name not in self.registered_events:
            return self._add_callback(event_name, callback)

        argspec = inspect.getargspec(callback)
        num_func_args = len(argspec.args)
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
                "(%d needed, %d given)" %
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
        self.logger.debug("Removed callback: %s" % callback_id)

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
        self.logger.info(
            "Calling %d callbacks for event: %s" %
            (len(callbacks), name)
        )

        accepted = False
        for callback_id, callback in callbacks.iteritems():
            try:
                callback(self.cardinal, *params)
                self.logger.debug(
                    "Callback %s accepted event: %s" %
                    (callback_id, name)
                )
                accepted = True
            # If this exception is received, the plugin told us not to set the
            # called flag true, so we can just log it and continue on. This
            # might happen if a plugin realizes the event does not apply to it
            # and wants the original caller to handle it normally.
            except EventRejectedMessage:
                self.logger.debug(
                    "Callback %s rejected event: %s" %
                    (callback_id, name)
                )
            except Exception:
                self.logger.exception(
                    "Exception during callback %s for event: %s" %
                    (callback_id, name)
                )

        return accepted

    def _add_callback(self, event_name, callback):
        """Adds a callback to the event's callback list and returns an ID.

        Keyword arguments:
          event_name -- Event name to add the callback to.
          callback -- The callback to add.

        Returns:
          string -- A callback ID to reference the callback with for removal.
        """
        callback_id = self._generate_id()
        while callback_id in self.registered_callbacks[event_name]:
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
