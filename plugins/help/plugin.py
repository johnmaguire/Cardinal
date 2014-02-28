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
    help.help = ["Shows loaded commands if no command is given. Otherwise, returns that command's help string.",
                 "Syntax: .help [command]"]

    def info(self, cardinal, user, channel, msg):
        cardinal.sendMsg(channel, "I am a Python-based Cardinal IRC bot. My owners are: %s. You can find out more about me on my Github page: http://johnmaguire2013.github.io/Cardinal" % self._get_owners(cardinal))

    info.commands = ['info']
    info.help = ["Gives some basic information about the bot.",
                 "Syntax: .info"]

def setup():
    return HelpPlugin()
