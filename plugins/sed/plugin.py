import re
from collections import defaultdict

from cardinal.decorators import event

ESCAPE_PLACEHOLDER = '!EsCaPeD SlASh!'


class SedPlugin(object):
    def __init__(self):
        self.history = defaultdict(dict)

    def substitute(self, user, channel, message):
        """Parse the message and return the substituted message or None.

        user -- The user_info tupled passed in to look up previous messages.
        message -- The message which may be a substitution.
        """
        # need to allow escaping slashes
        message = message.replace('\\/', ESCAPE_PLACEHOLDER)

        # check for substitution
        match = re.match('^s/(.+?)/(.+?)(?:/([gi]*))?$', message)
        if match is None:
            return None

        if match.group(2).count('/') > 0:
            # if this was intended to be a substitution, the syntax is invalid
            return None

        # replace placeholders after separating pattern from replacement
        pattern = match.group(1).replace(ESCAPE_PLACEHOLDER, '/')
        replacement = match.group(2).replace(ESCAPE_PLACEHOLDER, '/')

        count = 1
        flags = 0

        if match.group(3) and 'g' in match.group(3):
            count = 0
        if match.group(3) and 'i' in match.group(3):
            flags = re.IGNORECASE

        try:
            new_message = re.sub(
                re.escape(pattern),  # don't allow complex regex
                replacement,
                self.history[channel][user.nick],
                count,
                flags,
            )
        except KeyError:
            return None

        return new_message

    @event('irc.privmsg')
    def on_msg(self, cardinal, user, channel, message):
        new_message = self.substitute(user, channel, message)
        if new_message is not None:
            self.history[channel][user.nick] = new_message
            cardinal.sendMsg(channel, '{} meant: {}'.format(
                                user.nick, new_message))
        else:
            self.history[channel][user.nick] = message

    @event('irc.part')
    def on_part(self, cardinal, leaver, channel, message):
        if leaver.nick == cardinal.nickname:
            del self.history[channel]
        else:
            try:
                del self.history[channel][leaver.nick]
            except KeyError:
                pass

    @event('irc.kick')
    def on_kick(self, cardinal, kicker, channel, nick, reason):
        if nick == cardinal.nickname:
            del self.history[channel]
        else:
            try:
                del self.history[channel][nick]
            except KeyError:
                pass

    @event('irc.quit')
    def on_quit(self, cardinal, quitter, message):
        if quitter.nick == cardinal.nickname:
            self.history = defauldict(dict)
        else:
            for channel in self.history:
                try:
                    del self.history[channel][quitter.nick]
                except KeyError:
                    pass


def setup():
    return SedPlugin()
