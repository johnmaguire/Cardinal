import re

from twisted.internet import reactor
from twisted.internet.task import deferLater


def sleep(secs):
    """Async sleep function"""
    return deferLater(reactor, secs, lambda: None)


def strip_formatting(line):
    """Removes mIRC control code formatting"""
    return re.sub("(?:\x03\d\d?,\d\d?|\x03\d\d?|[\x01-\x1f])", "", line)

