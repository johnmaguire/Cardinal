from builtins import str
from builtins import object
import logging

from cardinal.bot import user_info
from cardinal.decorators import command, help


class AdminPlugin(object):
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)

        self.admins = []

        if config is None or not config.get('admins', False):
            self.logger.warning("No admins configured for admin plugin -- "
                                "copy config.example.json to config.json and "
                                "add your information.")
            return

        for admin in config['admins']:
            user = user_info(
                admin.get('nick', None),
                admin.get('user', None),
                admin.get('vhost', None),
            )

            if user.nick is None and user.user is None and user.vhost is None:
                self.logger.error(
                    "Invalid admin listed in admin plugin config -- at least "
                    "one of nick, user, or vhost must be present.")
                continue

            self.admins.append(user)

    def is_admin(self, user):
        """Compares a user against the registered admins."""
        for admin in self.admins:
            if (admin.nick is None or admin.nick == user.nick) and \
                    (admin.user is None or admin.user == user.user) and \
                    (admin.vhost is None or admin.vhost == user.vhost):
                return True

        return False

    @command('eval')
    @help("A super dangerous command that runs eval() on the input. "
          "(admin only)")
    @help("Syntax: .eval <command>")
    def eval(self, cardinal, user, channel, msg):
        if self.is_admin(user):
            command = ' '.join(msg.split()[1:])
            if len(command) > 0:
                try:
                    output = str(eval(command))
                    cardinal.sendMsg(channel, output)
                except Exception as e:
                    cardinal.sendMsg(channel, 'Exception %s: %s' %
                                              (e.__class__, e))
                    raise

    @command('exec')
    @help("A dangerous command that runs exec() on the input. " +
          "(admin only)")
    @help("Syntax: .exec <command>")
    def execute(self, cardinal, user, channel, msg):
        if self.is_admin(user):
            command = ' '.join(msg.split()[1:])
            if len(command) > 0:
                try:
                    exec(command)
                    cardinal.sendMsg(channel, "Ran exec() on input.")
                except Exception as e:
                    cardinal.sendMsg(channel, 'Exception %s: %s' %
                                              (e.__class__, e))
                    raise

    @command(['load', 'reload'])
    @help("If no plugins are given after the command, reload all plugins. "
          "Otherwise, load (or reload) the selected plugins. (admin only)")
    @help("Syntax: .load [plugin [plugin ...]]")
    def load_plugins(self, cardinal, user, channel, msg):
        if self.is_admin(user):
            cardinal.sendMsg(channel, "%s: Loading plugins..." % user.nick)

            plugins = msg.split()
            plugins.pop(0)

            if len(plugins) == 0:
                plugins = []
                for plugin in cardinal.plugin_manager:
                    plugins.append(plugin['name'])

            failed = cardinal.plugin_manager.load(plugins)

            successful = [
                plugin for plugin in plugins if plugin not in failed
            ]

            if len(successful) > 0:
                cardinal.sendMsg(channel, "Plugins loaded succesfully: %s." %
                                          ', '.join(sorted(successful)))

            if len(failed) > 0:
                cardinal.sendMsg(channel, "Plugins failed to load: %s." %
                                          ', '.join(sorted(failed)))

    @command('unload')
    @help("Unload selected plugins. (admin only)")
    @help("Syntax: .unload <plugin [plugin ...]>")
    def unload_plugins(self, cardinal, user, channel, msg):
        nick = user.nick

        if self.is_admin(user):
            plugins = msg.split()
            plugins.pop(0)

            if len(plugins) == 0:
                cardinal.sendMsg(channel, "%s: No plugins to unload." % nick)
                return

            cardinal.sendMsg(channel, "%s: Unloading plugins..." % nick)

            # Returns a list of plugins that weren't loaded to begin with
            unknown = cardinal.plugin_manager.unload(plugins)
            successful = [
                plugin for plugin in plugins if plugin not in unknown
            ]

            if len(successful) > 0:
                cardinal.sendMsg(channel, "Plugins unloaded succesfully: %s." %
                                          ', '.join(sorted(successful)))

            if len(unknown) > 0:
                cardinal.sendMsg(channel, "Unknown plugins: %s." %
                                          ', '.join(sorted(unknown)))

    @command('disable')
    @help("Disable plugins in a channel. (admin only)")
    @help("Syntax: .disable <plugin> <channel [channel ...]>")
    def disable_plugins(self, cardinal, user, channel, msg):
        if not self.is_admin(user):
            return

        channels = msg.split()
        channels.pop(0)

        if len(channels) < 2:
            cardinal.sendMsg(
                channel,
                "Syntax: .disable <plugin> <channel [channel ...]>")
            return

        cardinal.sendMsg(channel, "%s: Disabling plugins..." % user.nick)

        # First argument is plugin
        plugin = channels.pop(0)

        blacklisted = cardinal.plugin_manager.blacklist(plugin, channels)
        if not blacklisted:
            cardinal.sendMsg(channel, "Plugin %s does not exist" % plugin)
            return

        cardinal.sendMsg(channel, "Added to blacklist: %s." %
                                  ', '.join(sorted(channels)))

    @command('enable')
    @help("Enable plugins in a channel. (admin only)")
    @help("Syntax: .enable <plugin> <channel [channel ...]>")
    def enable_plugins(self, cardinal, user, channel, msg):
        if not self.is_admin(user):
            return

        channels = msg.split()
        channels.pop(0)

        if len(channels) < 2:
            cardinal.sendMsg(
                channel,
                "Syntax: .enable <plugin> <channel [channel ...]>")
            return

        cardinal.sendMsg(channel, "%s: Enabling plugins..." % user.nick)

        # First argument is plugin
        plugin = channels.pop(0)

        not_blacklisted = cardinal.plugin_manager.unblacklist(plugin, channels)
        if not_blacklisted is False:
            cardinal.sendMsg("Plugin %s does not exist" % plugin)

        successful = [
            channel_ for channel_ in channels
            if channel_ not in not_blacklisted
        ]

        if len(successful) > 0:
            cardinal.sendMsg(channel, "Removed from blacklist: %s." %
                                      ', '.join(sorted(successful)))

        if len(not_blacklisted) > 0:
            cardinal.sendMsg(channel, "Wasn't in blacklist: %s." %
                                      ', '.join(sorted(not_blacklisted)))

    @command('join')
    @help("Joins selected channels. (admin only)")
    @help("Syntax: .join <channel [channel ...]>")
    def join(self, cardinal, user, channel, msg):
        if self.is_admin(user):
            channels = msg.split()
            channels.pop(0)
            for channel in channels:
                cardinal.join(channel)

    @command('part')
    @help("Parts selected channels. (admin only)")
    @help("Syntax: .join <channel [channel ...]>")
    def part(self, cardinal, user, channel, msg):
        if not self.is_admin(user):
            return

        channels = msg.split()
        channels.pop(0)
        if len(channels) > 0:
            for channel in channels:
                cardinal.part(channel)
        elif channel != user:
            cardinal.part(channel)

    @command('quit')
    @help("Quits the network with a quit message, if one is defined. "
          "(admin only)")
    @help("Syntax: .quit [message]")
    def quit(self, cardinal, user, channel, msg):
        if self.is_admin(user):
            cardinal.disconnect(' '.join(msg.split(' ')[1:]))

    @command('dbg_quit')
    @help("Quits the network without setting disconnect flag "
          "(for testing reconnection, admin only)")
    @help("Syntax: .dbg_quit")
    def debug_quit(self, cardinal, user, channel, msg):
        if self.is_admin(user):
            cardinal.quit('Debug disconnect')


def setup(cardinal, config):
    """Returns an instance of the plugin.

    Keyword arguments:
      cardinal -- An instance of Cardinal. Passed in by PluginManager.
      config -- A config for this plugin.
    """
    return AdminPlugin(cardinal, config)
