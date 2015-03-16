class AdminPlugin(object):
    # A dictionary which will contain the owner nicks and vhosts
    owners = None

    # A list of trusted vhosts
    trusted_vhosts = None

    def __init__(self, cardinal, config):
        self.owners = {}
        self.trusted_vhosts = []

        # If owners aren't defined, bail out
        if not 'owners' in config:
            return

        # Loop through the owners in the config file and add them to the
        # instance's owner array.
        for owner in config['owners']:
            owner = owner.split('@')
            self.owners[owner[0]] = owner[1]
            self.trusted_vhosts.append(owner[1])

    # A command to quickly check whether a user has permissions to access
    # these commands.
    def is_owner(self, user):
        if user.group(3) in self.trusted_vhosts:
            return True

        return False

    def eval(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            command = ' '.join(msg.split()[1:])
            if len(command) > 0:
                try:
                    output = str(eval(command))
                    cardinal.sendMsg(channel, output)
                except Exception, e:
                    cardinal.sendMsg(channel, 'Exception %s: %s' % (e.__class__, e))
                    raise

    eval.commands = ['eval']
    eval.help = ["A super dangerous command that runs eval() on the input. (admin only)",
                 "Syntax: .eval <command>"]

    def execute(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            command = ' '.join(msg.split()[1:])
            if len(command) > 0:
                try:
                    exec(command)
                    cardinal.sendMsg(channel, "Ran exec() on input.")
                except Exception, e:
                    cardinal.sendMsg(channel, 'Exception %s: %s' % (e.__class__, e))
                    raise

    execute.commands = ['exec']
    execute.help = ["A super dangerous command that runs exec() on the input. (admin only)",
                    "Syntax: .exec <command>"]

    def load_plugins(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            cardinal.sendMsg(channel, "%s: Loading plugins..." % user.group(1))

            plugins = msg.split()
            plugins.pop(0)

            if len(plugins) == 0:
                plugins = []
                for plugin in cardinal.plugin_manager:
                    plugins.append(plugin['name'])

            failed_plugins = cardinal.plugin_manager.load(plugins)

            if failed_plugins:
                successful_plugins = [plugin for plugin in plugins if plugin not in failed_plugins]
                if len(successful_plugins) > 0:
                    cardinal.sendMsg(channel, "Plugins loaded succesfully: %s. Plugins failed to load: %s." % (', '.join(sorted(successful_plugins)), ', '.join(sorted(failed_plugins))))
                else:
                    cardinal.sendMsg(channel, "Plugins failed to load: %s." % ', '.join(sorted(failed_plugins)))
            else:
                cardinal.sendMsg(channel, "Plugins loaded successfully: %s." % ', '.join(sorted(plugins)))

    load_plugins.commands = ['load', 'reload']
    load_plugins.help = ["If no plugins are given after the command, reload all plugins. Otherwise, load (or reload) the selected plugins. (admin only)",
                         "Syntax: .reload [plugin [plugin ...]]"]

    def unload_plugins(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            plugins = msg.split()
            plugins.pop(0)

            if len(plugins) == 0:
                cardinal.sendMsg(channel, "%s: No plugins to unload." % user.group(1))
                return

            cardinal.sendMsg(channel, "%s: Unloading plugins..." % user.group(1))
            nonexistent_plugins = cardinal._unload_plugins(plugins)

            if nonexistent_plugins:
                unloaded_plugins = [plugin for plugin in plugins if plugin not in nonexistent_plugins]
                if len(unloaded_plugins) > 0:
                    cardinal.sendMsg(channel, "Plugins unloaded success: %s. Plugins that didn't exist: %s." % (', '.join(sorted(unloaded_plugins)), ', '.join(sorted(nonexistent_plugins))))
                else:
                    cardinal.sendMsg(channel, "Plugins didn't exist: %s." % ', '.join(sorted(nonexistent_plugins)))
            else:
                cardinal.sendMsg(channel, "Plugins unloaded success: %s." % ', '.join(sorted(plugins)))

    unload_plugins.commands = ['unload']
    unload_plugins.help = ["Unload selected plugins. (admin only)",
                           "Syntax: .unload <plugin [plugin ...]>"]

    def join(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            channels = msg.split()
            channels.pop(0)
            for channel in channels:
                cardinal.join(channel)

    join.commands = ['join']
    join.help = ["Joins selected channels. (admin only)",
                 "Syntax: .join <channel [channel ...]>"]

    def part(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            channels = msg.split()
            channels.pop(0)
            if len(channels) > 0:
                for channel in channels:
                    cardinal.part(channel)
            elif channel != user:
                cardinal.part(channel)

    part.commands = ['part']
    part.help = ["Parts selected channels. (admin only)",
                 "Syntax: .join <channel [channel ...]>"]

    def quit(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            cardinal.disconnect(' '.join(msg.split(' ')[1:]))

    quit.commands = ['quit']
    quit.help = ["Quits the network with a quit message, if one is defined. (admin only)",
                 "Syntax: .quit [message]"]

    def debug_quit(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            cardinal.quit('Debug disconnect')
    quit_debug.commands = ['dbg_quit']
    quit.help = ["Quits the network without setting disconnect flag (debug for reconnection, admin only)",
                 "Syntax: .dbg_quit"]

def setup(cardinal, config):
    """Returns an instance of the plugin.

    Keyword arguments:
      cardinal -- An instance of Cardinal. Passed in by PluginManager.
      config -- A config for this plugin.
    """
    return AdminPlugin(cardinal, config)
