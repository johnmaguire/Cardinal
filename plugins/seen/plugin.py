from datetime import datetime, timezone

from cardinal.decorators import command, help, event
from cardinal.util import (
    is_action,
    parse_action,
    strip_formatting,
)

PRIVMSG = 'PRIVMSG'  # [channel, message]
NOTICE = 'NOTICE'  # [channel, message]
NICK = 'NICK'  # [new_nick]
MODE = 'MODE'  # [channel, mode]
TOPIC = 'TOPIC'  # [channel, topic]
JOIN = 'JOIN'  # [channel]
PART = 'PART'  # [channel, message]
QUIT = 'QUIT'  # [message]

EPOCH = datetime.utcfromtimestamp(0)


class SeenPlugin:
    def __init__(self, cardinal, config):
        self.cardinal = cardinal
        self.ignored_channels = config.get('ignored_channels', [])

        self.db = cardinal.get_db('seen')
        with self.db() as db:
            if 'users' not in db:
                db['users'] = {}

            if 'tells' not in db:
                db['tells'] = {}

            # Fix case for old databases
            users = dict()
            for k, v in db['users'].items():
                users[k.lower()] = v
            db['users'] = users

    def update_user(self, nick, action, params):
        if not isinstance(params, list):
            raise TypeError("params must be a list")

        with self.db() as db:
            db['users'][nick.lower()] = {
                'timestamp': datetime.now(tz=timezone.utc).timestamp(),
                'action': action,
                'params': params,
            }

    @event('irc.privmsg')
    def irc_privmsg(self, cardinal, user, channel, message):
        if channel != cardinal.nickname and \
                channel not in self.ignored_channels:
            self.update_user(user.nick, PRIVMSG, [channel, message])

        self.do_tell(user.nick)

    @event('irc.notice')
    def irc_notice(self, cardinal, user, channel, message):
        if channel != cardinal.nickname and \
                channel not in self.ignored_channels:
            self.update_user(user.nick, NOTICE, [channel, message])

        self.do_tell(user.nick)

    @event('irc.mode')
    def irc_mode(self, cardinal, user, channel, mode):
        if channel not in self.ignored_channels:
            self.update_user(user.nick, MODE, [channel, mode])

        self.do_tell(user.nick)

    @event('irc.topic')
    def irc_topic(self, cardinal, user, channel, topic):
        if channel not in self.ignored_channels:
            self.update_user(user.nick, TOPIC, [channel, topic])

        self.do_tell(user.nick)

    @event('irc.join')
    def irc_join(self, cardinal, user, channel):
        if channel not in self.ignored_channels:
            self.update_user(user.nick, JOIN, [channel])

        self.do_tell(user.nick)

    @event('irc.part')
    def irc_part(self, cardinal, user, channel, reason):
        if channel not in self.ignored_channels:
            self.update_user(user.nick, PART, [channel, reason])

        self.do_tell(user.nick)

    @event('irc.nick')
    def irc_nick(self, cardinal, user, new_nick):
        self.update_user(user.nick, NICK, [new_nick])

        self.do_tell(user.nick)

    @event('irc.quit')
    def irc_quit(self, cardinal, user, reason):
        self.update_user(user.nick, QUIT, [reason])

    # TODO Add irc_kick/irc_kicked

    def do_tell(self, nick):
        with self.db() as db:
            if nick in db['tells']:
                for message in db['tells'][nick]:
                    self.cardinal.sendMsg(
                        nick,
                        f"{message['sender']} left a message: "
                        f"{message['message']}"
                    )

                self.cardinal.sendMsg(
                    nick,
                    "You can send a message to an offline user with "
                    ".tell <nick> <message>"
                )

                del db['tells'][nick]

    @staticmethod
    def _pretty_seconds(seconds):
        """Borrowed from the help plugin (_pretty_uptime)"""
        days, seconds = divmod(seconds, 60 * 60 * 24)
        hours, seconds = divmod(seconds, 60 * 60)
        minutes, seconds = divmod(seconds, 60)
        retval = "%d days " % days if days else ""
        retval += "%02d:%02d:%02d" % (hours, minutes, seconds)
        return retval

    def format_seen(self, nick):
        with self.db() as db:
            if nick.lower() not in db['users']:
                return "Sorry, I haven't seen {}.".format(nick)

            entry = db['users'][nick.lower()]

        dt_timestamp = datetime.fromtimestamp(
            entry['timestamp'],
            tz=timezone.utc,
        )
        t_seen = dt_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        t_ago = self._pretty_seconds((datetime
                                     .now(tz=timezone.utc)
                                     .replace(microsecond=0)
                                     - dt_timestamp).total_seconds())

        message = "I last saw {} {} ago ({}). ".format(nick, t_ago, t_seen)

        action, params = entry['action'], entry['params']
        if action == PRIVMSG:
            last_msg = params[1]
            if is_action(last_msg):
                last_msg = parse_action(nick, last_msg)

            message += "{} sent \"{}\" to {}.".format(
                nick,
                strip_formatting(last_msg),
                params[0],
            )
        elif action == NOTICE:
            message += "{} sent notice \"{}\" to {}.".format(
                nick,
                strip_formatting(params[1]),
                params[0],
            )
        elif action == JOIN:
            message += "{} joined {}.".format(nick, params[0])
        elif action == PART:
            message += "{} left {}{}.".format(
                nick,
                params[0],
                (" ({})".format(strip_formatting(params[1]))
                 if params[1] else
                 ""),
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
                strip_formatting(params[1]),
            )
        elif action == QUIT:
            message += "{} quit{}.".format(
                nick,
                (" ({})".format(strip_formatting(params[0]))
                 if params[0] else
                 ""),
            )

        return message

    @command('seen')
    @help("Returns the last time a user was seen, and their last action.")
    @help("Syntax: .seen <user>")
    def seen(self, cardinal, user, channel, msg):
        try:
            nick = msg.split(' ')[1]
        except IndexError:
            return cardinal.sendMsg(channel, 'Syntax: .seen <user>')

        if nick == user.nick:
            cardinal.sendMsg(channel, "{}: Don't be daft.".format(user.nick))
            return

        cardinal.sendMsg(channel, self.format_seen(nick))

    @command('tell')
    @help("Tell an offline user something when they come online.")
    @help("Syntax: .tell <nick> <message>")
    def tell(self, cardinal, user, channel, msg):
        try:
            nick, message = msg.split(' ', 2)[1:]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .tell <nick> <message>")
            return

        if nick == user.nick:
            cardinal.sendMsg(channel, "{}: Don't be daft.".format(user.nick))
            return

        with self.db() as db:
            tells = db['tells'].get(nick, [])
            tells.append({
                'sender': user.nick,
                'message': message,
            })
            db['tells'][nick] = tells

        cardinal.sendMsg(channel, f"{user.nick}: I'll let them know.")


entrypoint = SeenPlugin
