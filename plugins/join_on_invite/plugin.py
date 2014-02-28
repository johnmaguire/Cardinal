class InviteJoinPlugin(object):
    # A command to quickly check whether a user has permissions to access
    # these commands.
    def join_channel(self, cardinal, nick, channel):
        if nick == cardinal.nickname:
            cardinal.join(channel);
    join_channel.on_invite = True

def setup():
    return InviteJoinPlugin()
