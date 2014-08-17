import logging
import inspect
import linecache

class PluginManager(object):
    """Keeps track of, loads, and unloads plugins."""

    iteration_counter = 0
    """Holds our current iteration point"""

    cardinal = None
    """Instance of CardinalBot"""

    plugins = {}
    """List of loaded plugins"""

    def __init__(self, cardinal, plugins=None):
        """Creates a new instance, optionally with a list of plugins to load

        Keyword arguments:
          cardinal -- An instance of CardinalBot to pass to plugins.
          plugins -- A list of plugins to be loaded when instanced.

        Raises:
          ValueError -- When cardinal is not a CardinalBot instance.

        """
        logging.info("Initializing plugin manager")

        # To prevent circular dependencies, we can't sanity check this. Hope
        # for the best.
        self.cardinal = cardinal

        # Make sure we operate on a list
        if plugins is None:
            plugins = []

        for plugin in plugins:
            self.load_plugin(plugin)

    def __iter__(self):
        """Part of the iterator protocol, returns iterator object

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
        """Part of the iterator protocol, returns the next plugin

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

        # Make sure that the 
        if self.iteration_counter > len(keys):
            raise StopIteration

        return self.plugins[keys[self.iteration_counter - 1]]

    def _import_module(self, module, type='plugin'):
        """Given a plugin name, will import it from its directory or reload it

        If we are passing in a string, we can safely assume at this point that
        it's a plugin we've already loaded, so we just need to run reload() on
        it. However, if we're loading it fresh then we need to import it out
        of the plugins directory.

        Returns:
          object -- The module that was loaded.

        """
        if inspect.ismodule(module):
            return reload(module)
        elif isinstance(module, basestring):
            return importlib.import_module('plugins.%s.%s' % (module, type))

    def _create_plugin_instance(self, module):
        """Creates an instance of the plugin module

        If the setup() function of the plugin's module takes an argument then
        we will provide the instance of Cardinal to the plugin.

        Keyword arguments:
          module -- The module to instance.

        Returns:
          object -- The instance of the plugin.

        Raises:
          ValueError -- When a plugin's setup function has more than one
            argument.
        """
        argspec = inspect.getargspec(module.setup)
        if len(argspec.args) == 0:
            instance = module.setup()
        elif len(argspec.args) == 1:
            instance = module.setup(self.cardinal)
        else:
            raise ValueError("Plugin setup function must have 0 or 1 arguments")

        return instance

    def _get_plugin_commands(self, instance):
        """Find the commands in a plugin and return them as callables

        Keyword arguments:
          instance -- An instance of a plugin.

        Returns:
          list -- A list of callable commands.

        """
        commands = []

        for method in dir(instance):
            method = getattr(instance, method)
            if callable(method) and (hasattr(method, 'regex') or hasattr(method, 'commands')):
                commands.append(method)

        return commands

    def _get_plugin_events(self, instance):
        """Find the events in a plugin and return them as callables

        Valid events are as follows:
          on_join   -- When a user joins a channel.
          on_part   -- When a user parts a channel.
          on_kick   -- When a user is kicked from a channel.
          on_invite -- When a user invites another user to a channel.
          on_quit   -- When a user quits a channel.
          on_nick   -- When a user changes their nick.
          on_topic  -- When a user sets the topic of a channel.
          on_action -- When a user performs an ACTION on a channel.

        Keyword arguments:
          instance -- An instance of a plugin.

        Returns:
          list -- A list of callable events.

        """
        events = []

        for method in dir(instance):
            method = getattr(instance, method)
            if callable(method) and (hasattr(method, 'on_join') or hasattr(method, 'on_part') or
                                     hasattr(method, 'on_quit') or hasattr(method, 'on_kick') or
                                     hasattr(method, 'on_action') or hasattr(method, 'on_topic') or
                                     hasattr(method, 'on_nick') or hasattr(method, 'on_invite')):
                events.append(method)

        return events

    def load(self, name):
        """Takes either a plugin name or a list of plugins and loads them.

        This involves attempting to import the plugin's module, import the
        plugin's config module, instance the plugin's object, and finding its
        commands and events.

        Keyword arguments:
          name -- This can be a list of plugin names, or a single plugin name.

        Returns:
          list -- A list of failed plugins, or an empty list.

        Raises:
          ValueError -- When the name is not a string or list.

        """
        # Put it into a list if it's a string then make sure we have a list
        if isinstance(name, basestring):
        	name = [name.encode('utf-8')]
        if not isinstance(name, list):
            raise ValueError("Name must be a string or list of plugins")

        # List to hold failed plugins as a return value
        failed_plugins = []

        # This helps with debugging, as uncaught exceptions can show the wrong
        # data if the linecache isn't cleared
        linecache.clearcache()

        for plugin in name:
            logging.info("Attempting to load plugin: %s" % plugin)

            # Import each plugin's module with our own hacky function to reload
            # modules that have already been imported previously
            try:
                module = self._import_module(
                    self.plugins[plugin]['module'] if plugin in self.plugins else plugin
                )
            # If we fail to import it (usually a syntax error), then log an
            # error and move to the next plugin
            except Exception, e:
                logging.error("Could not load plugin module: %s (%s)" % (plugin, e))
                failed_plugins.append(plugin)

                continue

            # Attempt to load the config file for the given plugin.
            #
            # TODO: Change this to use ConfigParser
            config = None
            try:
                if plugin in self.plugins and 'config' in self.plugins[plugin]:
                    config = self._import_module(
                        self.plugins[plugin]['config'], 'config'
                    )
                else:
                    config = self._import_module(
                        plugin, 'config'
                    )
            # This is expected if the plugin doesn't have a config file
            except ImportError:
                logging.info("No config found for plugin: %s" % plugin)
            # This is usually do to a syntax error, so log a warning
            except Exception, e:
                logging.warning("Could not load plugin config: %s (%s)" % (plugin, e))

            # Instance the plugin
            try:
                instance = self._create_plugin_instance(module)
            except Exception, e:
                logging.error("Could not create plugin instance: %s (%s)" % (plugin, e))
                failed_plugins.append(plugin)

                continue

            commands = self._get_plugin_commands(instance)
            events = self._get_plugin_events(instance)

            if plugin in self.plugins:
                self.unload(plugin)

            self.plugins[plugin] = {
                'module': module,
                'instance': instance,
                'commands': commands,
                'events': events
            }

            logging.info("Plugin %s successfully loaded" % plugin)

        return failed_plugins

    def unload(self, plugins):
        """Takes either a plugin name or a list of plugins and unloads them.

        Simply validates whether we have loaded a plugin by a given name, and
        if so, clears all the data associated with it.

        Keyword arguments:
          name -- This can be a list of plugin names, or a single plugin name.

        Returns:
          list -- A list of failed plugins, or an empty list.

        Raises:
          ValueError -- When the name is not a string or list.

        """
        if isinstance(name, basestring):
            name = [name.encode('utf-8')]
        if not isinstance(name, list):
            raise ValueError("Name must be a string or list of plugins")

        # A list of plugins that weren't loaded in the first place
        failed_plugins = []

        for plugin in plugins:
            if plugin not in self.plugins:
                failed_plugins.append(plugin)
                continue

            # Check if the plugin has a method named close
            if (hasattr(self.plugins[plugin]['instance'], 'close') and
                inspect.ismethod(self.plugins[plugin]['instance'].close)):
                # Check if we should pass in the CardinalBot instance or not
                argspec = inspect.getargspec(self.plugins[plugin]['instance'].close)
                if len(argspec.args) == 1:
                    instance = module.close()
                elif len(argspec.args) == 2:
                    instance = module.close(self.cardinal)
                else:
                    logging.error("Plugin %s's close method must have 1 or 2 arguments" % plugin)

            # Unassign the plugin and Python will do GC soon
            del self.plugins[plugin]

        return failed_plugins
