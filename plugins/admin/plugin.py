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

from plugins.admin import config

class AdminPlugin(object):
    # A dictionary which will contain the owner nicks and vhosts
    owners = {}

    # A list of trusted vhosts
    trusted_vhosts = []

    def __init__(self):
        # Loop through the owners in the config file and add them to the
        # instance's owner array.
        for owner in config.OWNERS:
            owner = owner.split('@')
            self.owners[owner[0]] = owner[1]
            self.trusted_vhosts.append(owner[1])

    # A command to quickly check whether a user has permissions to access
    # these commands.
    def is_owner(self, user):
        if user.group(3) in self.trusted_vhosts:
            return True

        return False

    def reload_plugins(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            cardinal.sendMsg(channel, "%s: Reloading plugins..." % user.group(1))
            
            plugins = msg.split()
            plugins.pop(0)

            if len(plugins) == 0:
                plugins = []
                for name, module in cardinal.loaded_plugins.items():
                    plugins.append(name)

            failed_plugins = cardinal._load_plugins(plugins)

            if failed_plugins:
                successful_plugins = [plugin for plugin in plugins if plugin not in failed_plugins]
                if len(successful_plugins) > 0:
                    cardinal.sendMsg(channel, "Plugins loaded success: %s. Plugins loaded failure: %s." % (', '.join(successful_plugins), ', '.join(failed_plugins)))
                else:
                    cardinal.sendMsg(channel, "Plugins loaded failure: %s." % ', '.join(failed_plugins))
            else:
                cardinal.sendMsg(channel, "Plugins loaded success: %s." % ', '.join(plugins))

    reload_plugins.commands = ['reload']

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
                    cardinal.sendMsg(channel, "Plugins unloaded success: %s. Plugins that didn't exist: %s." % (', '.join(unloaded_plugins), ', '.join(nonexistent_plugins)))
                else:
                    cardinal.sendMsg(channel, "Plugins didn't exist: %s." % ', '.join(nonexistent_plugins))
            else:
                cardinal.sendMsg(channel, "Plugins unloaded success: %s." % ', '.join(plugins))

    unload_plugins.commands = ['unload']

    def join(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            channels = msg.split()
            channels.pop(0)
            for channel in channels:
                cardinal.join(channel)

    join.commands = ['join']

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

    def quit(self, cardinal, user, channel, msg):
        if self.is_owner(user):
            cardinal.disconnect(msg[6:])

    quit.commands = ['quit']

def setup():
    return AdminPlugin()
