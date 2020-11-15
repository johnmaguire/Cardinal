from builtins import object
from cardinal.decorators import event


class TestEventCallbackPlugin(object):
    def __init__(self):
        self.cardinal = None
        self.messages = []

    @event('irc.raw')
    def irc_raw_callback(self, cardinal, message):
        self.cardinal = cardinal
        self.messages.append(message)


def setup():
    return TestEventCallbackPlugin()
