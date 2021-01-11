from builtins import object
import re

from twisted.internet import reactor
from twisted.internet.task import deferLater


def is_action(message):
    """Checks if a message is a /me message."""
    return message.startswith("\x01ACTION")


def parse_action(nick, message):
    """Parses a /me message like an IRC client might.

    e.g. "/me dances." -> "* Cardinal dances."
    """
    if not is_action(message):
        raise ValueError("This message is not an ACTION message")

    message = message[len("\x01ACTION "):]
    if message[-1] == "\x01":
        message = message[:-1]

    return "* {} {}".format(
        nick,
        message,
    )


def sleep(secs):
    """Async sleep function"""
    return deferLater(reactor, secs, lambda: None)


def strip_formatting(line):
    """Removes mIRC control code formatting"""
    return re.sub(r"(?:\x03\d\d?,\d\d?|\x03\d\d?|[\x01-\x1f])", "", line)


class formatting(object):
    class color(object):
        @staticmethod
        def white(text):
            return "\x0300{}\x03".format(text)

        @staticmethod
        def black(text):
            return "\x0301{}\x03".format(text)

        @staticmethod
        def blue(text):
            return "\x0302{}\x03".format(text)

        @staticmethod
        def green(text):
            return "\x0303{}\x03".format(text)

        @staticmethod
        def light_red(text):
            return "\x0304{}\x03".format(text)

        @staticmethod
        def brown(text):
            return "\x0305{}\x03".format(text)

        @staticmethod
        def purple(text):
            return "\x0306{}\x03".format(text)

        @staticmethod
        def orange(text):
            return "\x0307{}\x03".format(text)

        @staticmethod
        def yellow(text):
            return "\x0308{}\x03".format(text)

        @staticmethod
        def light_green(text):
            return "\x0309{}\x03".format(text)

        @staticmethod
        def cyan(text):
            return "\x0310{}\x03".format(text)

        @staticmethod
        def light_cyan(text):
            return "\x0311{}\x03".format(text)

        @staticmethod
        def light_blue(text):
            return "\x0312{}\x03".format(text)

        @staticmethod
        def pink(text):
            return "\x0313{}\x03".format(text)

        @staticmethod
        def grey(text):
            return "\x0314{}\x03".format(text)
        gray = grey

        @staticmethod
        def light_grey(text):
            return "\x0315{}\x03".format(text)
        light_gray = light_grey

    # alias as this will be used commonly
    C = color

    reset = "\x03"

# alias as this will be used commonly
F = formatting
