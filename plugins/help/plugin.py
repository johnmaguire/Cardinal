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

class HelpPlugin(object):
    def _get_owners(self, cardinal):
        owners = False
        if 'admin' in cardinal.config:
            owners = []
            for owner in cardinal.config['admin'].OWNERS:
                owner = owner.split('@')
                owners.append(owner[0])
            
            owners = list(set(owners))

        return ', '.join(owners) if owners else 'No registered owners.'

    def _get_commands(self, cardinal):
        commands = []
        
        # Loop through commands registered in Cardinal
        for name, module in cardinal.loaded_plugins.items():
            for command in module['commands']:
                if hasattr(command, 'commands'):
                    commands.append(command.commands[0])
                elif hasattr(command, 'name'):
                    commands.append(command.name)

        return commands

    def _get_command_help(self, cardinal, help_command):
        help_text = 'No help found for that command.'

        # Check each module for the command being searched for
        for name, module in cardinal.loaded_plugins.items():
            found_command = None

            for command in module['commands']:
                # First check if the command responds to the requested command
                if hasattr(command, 'commands') and help_command in command.commands:
                    found_command = command
                    break

                # Check if the command's name is the requested command
                if hasattr(command, 'name') and help_command == command.name:
                    found_command = command
                    break

            # Return the help text for the command found if it exists
            if found_command:
                return found_command.help if hasattr(found_command, 'help') else 'No help found for that command.'

        # Didn't find the command, so return a command does not exist error
        return 'Command does not exist.'

    # Give the user a list of valid commands in the bot if no command is
    # provided. If a valid command is provided, return its 
    def help(self, cardinal, user, channel, msg):
        parameters = msg.split()
        if len(parameters) == 1:
            cardinal.sendMsg(channel, "Loaded commands: %s" % ', '.join(self._get_commands(cardinal)))
        else:
            command = parameters[1]
            help = self._get_command_help(cardinal, command)
            if isinstance(help, list):
                for help_line in help:
                    cardinal.sendMsg(channel, help_line)
            elif isinstance(help, basestring):
                cardinal.sendMsg(channel, help)
            else:
                cardinal.sendMsg(channel, "Unable to handle help string returned by module.")

    help.commands = ['help']
    help.help = ["Shows loaded commands if no command is given. Otherwise, returns that command's help string.", "Syntax: .help [command]"]

    def owners(self, cardinal, user, channel, msg):
        cardinal.sendMsg(channel, "Owners: %s" % self._get_owners(cardinal))

    owners.commands = ['owners']
    owners.help = "Shows a list of nicks registered as owners of the bot."

def setup():
    return HelpPlugin()
