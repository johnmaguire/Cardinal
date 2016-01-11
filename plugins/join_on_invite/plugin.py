from cardinal.decorators import event


class InviteJoinPlugin(object):
    """Simple plugin that joins a channel if an invite is given."""

    @event('irc.invite')
    def join_channel(self, cardinal, user, channel):
        """Callback for irc.invite that joins a channel"""
        cardinal.join(channel)


def setup(cardinal):
    return InviteJoinPlugin()
