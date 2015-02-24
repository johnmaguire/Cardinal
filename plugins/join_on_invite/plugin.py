class InviteJoinPlugin(object):
    """Simple plugin that joins a channel if an invite is given."""

    callback_id = None
    """ID generated when callback was added for the irc.invite event"""

    def __init__(self, cardinal):
        """Register our callback and save the callback ID"""
        self.callback_id = cardinal.event_manager.register_callback("irc.invite", self.join_channel)

    def join_channel(self, cardinal, user, channel):
        """Callback for irc.invite that joins a channel"""
        cardinal.join(channel);

    def close(self, cardinal):
        """When the plugin is closed, removes our callback"""
        cardinal.event_manager.remove_callback("irc.invite", self.callback_id)

def setup(cardinal):
    return InviteJoinPlugin(cardinal)
