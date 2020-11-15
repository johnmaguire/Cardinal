from builtins import object
from cardinal.decorators import command


class TestCommandRaisesExceptionPlugin(object):
    def __init__(self):
        self.command_calls = []

    @command('command')
    def command(self, *args):
        self.command_calls.append(args)
        raise Exception()


def setup():
    return TestCommandRaisesExceptionPlugin()
