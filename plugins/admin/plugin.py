class AdminPlugin(object):
    # A dictionary which will contain the owner nicks and vhosts
    owners = None

    # A list of trusted vhosts
    trusted_vhosts = None

    def __init__(self, cardinal, config):
        self.owners = {}
        self.trusted_vhosts = []

        # If owners aren't defined, bail out
        if 'owners' not in config:
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
                    cardinal.sendMsg(channel, 'Exception %s: %s' %
                                              (e.__class__, e))
                    raise

    eval.commands = ['eval']
    eval.help = ["A super dangerous command that runs eval() on the input. " +
                 "(admin only)",

                 "Syntax: .eval <command>"]

    def execute(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            command = ' '.join(msg.split()[1:])
            if len(command) > 0:
                try:
                    exec(command)
                    cardinal.sendMsg(channel, "Ran exec() on input.")
                except Exception, e:
                    cardinal.sendMsg(channel, 'Exception %s: %s' %
                                              (e.__class__, e))
                    raise

    execute.commands = ['exec']
    execute.help = ["A dangerous command that runs exec() on the input. " +
                    "(admin only)",

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

            deferred = cardinal.plugin_manager.load(plugins)
            def handle_results(plugins):
                states = {True: [], False: []}
                for success, plugin in plugins:
                    states[success].append(plugin)

                if len(states[True]) > 0:
                    cardinal.sendMsg(channel, "Plugins loaded succesfully: %s." %
                                              ', '.join(sorted(states[True])))

                if len(states[False]) > 0:
                    cardinal.sendMsg(channel, "Plugins failed to load: %s." %
                                              ', '.join(sorted(states[False])))

            deferred.addCallback(handle_results)


    load_plugins.commands = ['load', 'reload']
    load_plugins.help = ["If no plugins are given after the command, reload " +
                         "all plugins. Otherwise, load (or reload) the " +
                         "selected plugins. (admin only)",

                         "Syntax: .reload [plugin [plugin ...]]"]

    def unload_plugins(self, cardinal, user, channel, msg):
        nick = user.group(1)

        if self.is_owner(user):
            plugins = msg.split()
            plugins.pop(0)

            if len(plugins) == 0:
                cardinal.sendMsg(channel, "%s: No plugins to unload." % nick)
                return

            cardinal.sendMsg(channel, "%s: Unloading plugins..." % nick)

            # Returns a list of plugins that weren't loaded to begin with
            deferred = cardinal.plugin_manager.unload(plugins)
            def handle_results(plugins):
                states = {True: [], False: []}
                for success, plugin in plugins:
                    states[success].append(plugin)

                if len(states[True]) > 0:
                    cardinal.sendMsg(channel, "Plugins unloaded succesfully: %s." %
                                              ', '.join(sorted(states[True])))

                if len(states[False]) > 0:
                    cardinal.sendMsg(channel, "Unknown plugins: %s." %
                                              ', '.join(sorted(states[False])))

            deferred.addCallback(handle_results)

    unload_plugins.commands = ['unload']
    unload_plugins.help = ["Unload selected plugins. (admin only)",
                           "Syntax: .unload <plugin [plugin ...]>"]

    def disable_plugins(self, cardinal, user, channel, msg):
        if not self.is_owner(user):
            return

        channels = msg.split()
        channels.pop(0)

        if len(channels) < 2:
            cardinal.sendMsg(channel,
                             "Syntax: .disable <plugin> <channel [channel ...]>")
            return

        cardinal.sendMsg(channel, "%s: Disabling plugins..." % user.group(1))

        # First argument is plugin
        plugin = channels.pop(0)

        blacklisted = cardinal.plugin_manager.blacklist(plugin, channels)
        if not blacklisted:
            cardinal.sendMsg(channel, "Plugin %s does not exist" % plugin)
            return

        cardinal.sendMsg(channel, "Added to blacklist: %s." %
                                  ', '.join(sorted(channels)))

    disable_plugins.commands = ['disable']
    disable_plugins.help = ["Disable plugins in a channel. (admin only)",
                            "Syntax: .disable <plugin> <channel [channel ...]>"]

    def enable_plugins(self, cardinal, user, channel, msg):
        if not self.is_owner(user):
            return

        channels = msg.split()
        channels.pop(0)

        if len(channels) < 2:
            cardinal.sendMsg(channel,
                             "Syntax: .enable <plugin> <channel [channel ...]>")
            return

        cardinal.sendMsg(channel, "%s: Enabling plugins..." % user.group(1))

        # First argument is plugin
        plugin = channels.pop(0)

        not_blacklisted = cardinal.plugin_manager.unblacklist(plugin, channels)
        if not_blacklisted is False:
            cardinal.sendMsg("Plugin %s does not exist" % plugin)

        successful = [
            channel for channel in channels if channel not in not_blacklisted
        ]

        if len(successful) > 0:
            cardinal.sendMsg(channel, "Removed from blacklist: %s." %
                                      ', '.join(sorted(successful)))

        if len(not_blacklisted) > 0:
            cardinal.sendMsg(channel, "Wasn't in blacklist: %s." %
                                      ', '.join(sorted(not_blacklisted)))

    enable_plugins.commands = ['enable']
    enable_plugins.help = ["Enable plugins in a channel. (admin only)",
                           "Syntax: .enable <plugin> <channel [channel ...]>"]

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
        if not self.is_owner(user):
            return

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
    quit.help = ["Quits the network with a quit message, if one is defined. " +
                 "(admin only)",

                 "Syntax: .quit [message]"]

    def debug_quit(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            cardinal.quit('Debug disconnect')
    debug_quit.commands = ['dbg_quit']
    debug_quit.help = ["Quits the network without setting disconnect flag " +
                       "(for testing reconnection, admin only)",

                       "Syntax: .dbg_quit"]


def setup(cardinal, config):
    """Returns an instance of the plugin.

    Keyword arguments:
      cardinal -- An instance of Cardinal. Passed in by PluginManager.
      config -- A config for this plugin.
    """
    return AdminPlugin(cardinal, config)
