from datetime import datetime
from cardinal.decorators import command, help


# Command prefix placeholder to look for when performing string replace on 
# the syntax help message.
PREFIX_PLACEHOLDER = '@'


class HelpPlugin:
    def __init__(self, cmd_prefix):
        self._cmd_prefix = cmd_prefix

    # Gets a list of admins from the admin plugin instantiated within the
    # Cardinal instance, if exists
    def _get_admins(self, cardinal):
        admins = False
        admin_config = cardinal.config('admin')
        if admin_config is not None and 'admins' in admin_config:
            admins = []
            for admin in admin_config['admins']:
                admins.append(admin['nick'])

            admins = sorted(list(set(admins)))

        return ', '.join(admins) if admins else '(no registered admins)'

    # Pulls a list of all commands from Cardinal instance, using either the
    # first defined command alias or failing that, the command's name
    def _get_commands(self, cardinal):
        commands = []

        # Loop through commands registered in Cardinal
        for plugin in cardinal.plugin_manager:
            for cmd in plugin['commands']:
                if hasattr(cmd, 'commands'):
                    commands.append(cmd.commands[0])
                elif hasattr(cmd, 'name'):
                    commands.append(cmd.name)

        return commands

    # Gets the help text out of the Cardinal instance for a given command
    def _get_command_help(self, cardinal, help_command):
        help_text = 'No help found for that command.'

        # Check each module for the command being searched for
        for plugin in cardinal.plugin_manager:
            found_command = False

            for cmd in plugin['commands']:
                # Check if the command responds with the command the user
                # requested
                if hasattr(cmd, 'commands') and \
                        help_command in cmd.commands:
                    found_command = cmd
                    break

            # If the command was found and has a help file, set the help_text
            if found_command and hasattr(found_command, 'help'):
                help_text = found_command.help

            # Return the help text for the command found if it exists
            if found_command:
                return help_text

        # Didn't find the command, so return a command does not exist error
        return 'Command does not exist.'

    # Pulls relevant meta information from the Cardinal instance
    def _get_meta(self, cardinal):
        return {
            'uptime':  cardinal.uptime,
            'booted':  cardinal.booted,
        }

    # Given a number of seconds, converts it to a readable uptime string
    def _pretty_uptime(self, seconds):
        days, seconds = divmod(seconds, 60 * 60 * 24)
        hours, seconds = divmod(seconds, 60 * 60)
        minutes, seconds = divmod(seconds, 60)
        uptime = "%d days " % days if days else ""
        uptime += "%02d:%02d:%02d" % (hours, minutes, seconds)

        return uptime

    # Replace the command prefix placeholder (@) with the user-defined prefix
    def _replace_prefix(self, help_msg):
        if isinstance(help_msg, list):
            correct_help_msg = [line.replace(PREFIX_PLACEHOLDER, self._cmd_prefix) for line in help_msg]
        else:
            correct_help_msg = help_msg.replace(PREFIX_PLACEHOLDER, self._cmd_prefix)
        return correct_help_msg

    # Give the user a list of valid commands in the bot if no command is
    # provided. If a valid command is provided, return its help text
    @command(['help'])
    @help("Shows loaded commands or a specific command's help.")
    @help("Syntax: @help [command]")
    def cmd_help(self, cardinal, user, channel, msg):
        parameters = msg.split()
        if len(parameters) == 1:
            cardinal.sendMsg(
                channel,
                "Loaded commands: %s" % ', '.join(self._get_commands(cardinal))
            )
        else:
            command = parameters[1]
            help = self._get_command_help(cardinal, command)
            help = self._replace_prefix(help)
            if isinstance(help, list):
                for help_line in help:
                    cardinal.sendMsg(channel, help_line)
            elif isinstance(help, str):
                cardinal.sendMsg(channel, help)
            else:
                cardinal.sendMsg(
                    channel,
                    "Unable to handle help string returned by module.")

    # Sends some basic meta information about the bot
    @command('info')
    @help("Gives some basic information about the bot.")
    @help("Syntax: @info")
    def cmd_info(self, cardinal, user, channel, msg):
        admins = self._get_admins(cardinal)
        meta = self._get_meta(cardinal)

        # Calculate uptime into readable format
        now = datetime.now()
        uptime = self._pretty_uptime((now - meta['uptime']).total_seconds())
        booted = self._pretty_uptime((now - meta['booted']).total_seconds())

        cardinal.sendMsg(
            channel,
            "I am a Python 3 IRC bot, online since {}. I initially connected "
            "{} ago. My admins are: {}. Use .help to list commands."
            .format(uptime, booted, admins)
        )
        cardinal.sendMsg(
            channel,
            "Visit https://github.com/JohnMaguire/Cardinal to learn more."
        )


entrypoint = HelpPlugin
