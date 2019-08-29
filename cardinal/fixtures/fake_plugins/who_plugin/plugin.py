import logging

from cardinal.decorators import command
from twisted.internet import defer


class WhoExamplePlugin(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info('started')

    @command('who_example')
    @defer.inlineCallbacks
    def cmd(self, cardinal, user, channel, msg):
        self.logger.msg('fetching users')
        users = yield cardinal.who(channel)
        self.logger.info('users: {}'.format(users))


def setup():
    return WhoExamplePlugin()
