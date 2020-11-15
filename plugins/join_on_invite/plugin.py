from builtins import object
from cardinal.decorators import event


class InviteJoinPlugin(object):
    """Simple plugin that joins a channel if an invite is given."""

    def __init__(self, cardinal, config):
        self.rejoin_on_kick = False
        if config:
            self.rejoin_on_kick = config.get('rejoin_on_kick', False)

    @event('irc.invite')
    def join_channel(self, cardinal, user, channel):
        """Callback for irc.invite that joins a channel"""
        cardinal.join(channel)

    @event('irc.kick')
    def rejoin_channel(self, cardinal, user, channel, nick, reason):
        if not self.rejoin_on_kick:
            return

        if nick == cardinal.nickname:
            cardinal.join(channel)


def setup(cardinal, config):
    return InviteJoinPlugin(cardinal, config)
