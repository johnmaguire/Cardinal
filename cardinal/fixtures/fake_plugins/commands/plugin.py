from builtins import object
from cardinal.decorators import command, regex


class TestCommandsPlugin(object):
    def __init__(self):
        self.command1_calls = []
        self.command2_calls = []
        self.regex_command_calls = []

    @command(['command1', 'command1_alias'])
    def command1(self, *args):
        self.command1_calls.append(args)

    @command('command2')
    def command2(self, *args):
        self.command2_calls.append(args)

    @regex('^regex')
    def regex_command(self, *args):
        self.regex_command_calls.append(args)


def setup():
    return TestCommandsPlugin()
