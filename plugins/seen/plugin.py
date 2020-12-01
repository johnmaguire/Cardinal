from datetime import datetime, timezone

from cardinal.decorators import command, help, event

PRIVMSG = 'PRIVMSG'  # [channel, message]
NOTICE = 'NOTICE'  # [channel, message]
NICK = 'NICK'  # [new_nick]
MODE = 'MODE'  # [channel, mode]
TOPIC = 'TOPIC'  # [channel, topic]
JOIN = 'JOIN'  # [channel]
PART = 'PART'  # [channel, message]
QUIT = 'QUIT'  # [message]

EPOCH = datetime.utcfromtimestamp(0)


class SeenPlugin(object):
    def __init__(self, cardinal):
        self.db = cardinal.get_db('seen')
        with self.db() as db:
            if 'users' not in db:
                db['users'] = {}

    def update_user(self, nick, action, params):
        if not isinstance(params, list):
            raise TypeError("params must be a list")

        with self.db() as db:
            db['users'][nick] = {
                'timestamp': datetime.now(tz=timezone.utc).timestamp(),
                'action': action,
                'params': params,
            }

    @event('irc.privmsg')
    def irc_privmsg(self, cardinal, user, channel, message):
        if channel != cardinal.nickname:  # we want to ignore private messages
            self.update_user(user.nick, PRIVMSG, [channel, message])

    @event('irc.notice')
    def irc_notice(self, cardinal, user, channel, message):
        if channel != cardinal.nickname:  # we want to ignore private notices
            self.update_user(user.nick, NOTICE, [channel, message])

    @event('irc.nick')
    def irc_nick(self, cardinal, user, new_nick):
        self.update_user(user.nick, NICK, [new_nick])

    @event('irc.mode')
    def irc_mode(self, cardinal, user, channel, mode):
        self.update_user(user.nick, MODE, [channel, mode])

    @event('irc.topic')
    def irc_topic(self, cardinal, user, channel, topic):
        self.update_user(user.nick, TOPIC, [channel, topic])

    @event('irc.join')
    def irc_join(self, cardinal, user, channel):
        self.update_user(user.nick, JOIN, [channel])

    @event('irc.part')
    def irc_part(self, cardinal, user, channel, reason):
        self.update_user(user.nick, PART, [channel, reason])

    @event('irc.quit')
    def irc_quit(self, cardinal, user, reason):
        self.update_user(user.nick, QUIT, [reason])

    def format_seen(self, nick):
        with self.db() as db:
            if nick not in db['users']:
                return "I've never seen {} before.".format(nick)

            entry = db['users'][nick]

        dt_timestamp = datetime.fromtimestamp(
            entry['timestamp'],
            tz=timezone.utc,
        )
        t_seen = str(dt_timestamp)
        t_ago = str(datetime
                    .now(tz=timezone.utc)
                    .replace(microsecond=0) - dt_timestamp)

        message = "I last saw {} at {} ({} ago). ".format(nick, t_seen, t_ago)

        action, params = entry['action'], entry['params']
        if action == PRIVMSG:
            message += "{} sent \"{}\" to {}.".format(
                nick,
                params[1],
                params[0],
            )
        elif action == NOTICE:
            message += "{} sent notice \"{}\" to {}.".format(
                nick,
                params[1],
                params[0],
            )
        elif action == JOIN:
            message += "{} joined {}.".format(nick, params[0])
        elif action == PART:
            message += "{} left {}{}.".format(
                nick,
                params[0],
                " ({})".format(params[1]) if params[1] else "",
            )
        elif action == NICK:
            message += "{} renamed themselves {}.".format(nick, params[0])
        elif action == MODE:
            message += "{} set mode {} on channel {}.".format(
                nick,
                params[1],
                params[0],
            )
        elif action == TOPIC:
            message += "{} set {}'s topic to \"{}\".".format(
                nick,
                params[0],
                params[1],
            )
        elif action == QUIT:
            message += "{} quit{}.".format(
                nick,
                " ({})".format(params[0]) if params[0] else "",
            )

        return message

    @command('seen')
    @help("Returns the last time a user was seen, and their last action.")
    @help("Syntax: .seen <user>")
    def seen(self, cardinal, user, channel, msg):
        try:
            nick = msg.split(' ', 1)[1]
        except IndexError:
            return cardinal.sendMsg(channel, 'Syntax: .seen <user>')

        if nick == user.nick:
            cardinal.sendMsg(channel, "{}: Don't be daft.".format(user.nick))
            return

        cardinal.sendMsg(channel, self.format_seen(nick))


def setup(cardinal):
    return SeenPlugin(cardinal)
