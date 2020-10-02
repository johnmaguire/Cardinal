from datetime import datetime

from cardinal.decorators import command, help, regex, event


class SeenPlugin(object):
    def __init__(self, cardinal):
        self.users_seen = dict()
        self.users_action = dict()

    @event('irc.privmsg')
    def irc_privmsg(self, cardinal, user, channel, message):
        nick = user[0]

        if channel != cardinal.nickname: # we want to ignore private messages
            self.users_seen[nick] = datetime.now().replace(microsecond=0)
            self.users_action[nick] = "sent message \"{}\" in channel {}.".format(message, channel)

    @event('irc.notice')
    def irc_notice(self, cardinal, user, channel, message):
        nick = user[0]

        if channel != cardinal.nickname: # we want to ignore private notices
            self.users_seen[nick] = datetime.now().replace(microsecond=0)
            self.users_action[nick] = "sent notice \"{}\" in channel {}.".format(message, channel)

    @event('irc.nick')
    def irc_nick(self, cardinal, user, new_nick):
        nick = user[0]

        self.users_seen[nick] = datetime.now().replace(microsecond=0)
        self.users_action[nick] = "changed nick to {}.".format(new_nick)

    @event('irc.mode')
    def irc_mode(self, cardinal, user, channel, mode):
        nick = user[0]

        self.users_seen[nick] = datetime.now().replace(microsecond=0)
        self.users_action[nick] = "set mode {} on channel {}.".format(mode, channel)

    @event('irc.topic')
    def irc_topic(self, cardinal, user, channel, topic):
        nick = user[0]

        self.users_seen[nick] = datetime.now().replace(microsecond=0)
        self.users_action[nick] = "set topic for channel {} to {}.".format(channel, topic)

    @event('irc.join')
    def irc_join(self, cardinal, user, channel):
        nick = user[0]

        self.users_seen[nick] = datetime.now().replace(microsecond=0)
        self.users_action[nick] = "joined channel {}.".format(channel)

    @event('irc.part')
    def irc_part(self, cardinal, user, channel, reason):
        nick = user[0]

        part_reason = " with reason {}".format(reason) if reason else ""

        self.users_seen[nick] = datetime.now().replace(microsecond=0)
        self.users_action[nick] = "parted channel {}{}.".format(channel, part_reason)

    @event('irc.quit')
    def irc_quit(self, cardinal, user, reason):
        nick = user[0]

        quit_reason = " with reason {}".format(reason) if reason else ""

        self.users_seen[nick] = datetime.now().replace(microsecond=0)
        self.users_action[nick] = "quit{}.".format(quit_reason)

    @command(['seen', 'lastseen'])
    @help("Returns the last time a user was seen, and their last action.")
    @help("Syntax: .seen <user>")
    def seen(self, cardinal, user, channel, msg):
        try:
            nick = msg.split(' ', 1)[1]
        except IndexError:
            return cardinal.sendMsg(channel, 'Syntax: .seen <user>')

        user_seen = self.users_seen.get(nick)
        user_action = self.users_action.get(nick)

        if user_seen is not None:
            t_seen = str(user_seen)
            t_ago = str(datetime.now().replace(microsecond=0) - user_seen)

            cardinal.sendMsg(channel, "User {} last seen at {} ({} ago).".format(nick, t_seen, t_ago))
            cardinal.sendMsg(channel, "Last action: {}".format(user_action))
        else:
            cardinal.sendMsg(channel, "User {} not found.".format(nick))

def setup(cardinal):
    return SeenPlugin(cardinal)
