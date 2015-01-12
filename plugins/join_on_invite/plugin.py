class InviteJoinPlugin(object):
    def __init__(self, cardinal):
        cardinal.event_manager.register_callback("irc.invite", self.join_channel)

    def join_channel(self, cardinal, user, channel):
        cardinal.join(channel);

def setup(cardinal):
    return InviteJoinPlugin(cardinal)
