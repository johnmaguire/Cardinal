import pytest
from mock import Mock

from cardinal.bot import user_info
from plugins.sed.plugin import SedPlugin


@pytest.mark.parametrize("message,new_message", [
    ('s/i/X', 'thXs is a test message'),
    ('s/i/X/g', 'thXs Xs a test message'),
    ('s/I/X', 'this is a test message'),
    ('s/I/X/i', 'thXs is a test message'),
    ('s/I/X/ig', 'thXs Xs a test message'),
    ('s/I/X/gi', 'thXs Xs a test message'),
    ('s/I/X/ggii', 'thXs Xs a test message'),
])
def test_substitute_modifiers(message, new_message):
    user = user_info('user', None, None)
    channel = '#channel'

    plugin = SedPlugin()
    plugin.history[channel][user] = 'this is a test message'

    assert plugin.substitute(user, channel, message) == new_message


@pytest.mark.parametrize("message,new_message", [
    ('s/\//X', 'hiXhey/hello'),
    ('s/\//X/g', 'hiXheyXhello'),
    ('s/hi/\//', '//hey/hello'),
    ('s/hi/hey//', None),
])
def test_substitute_escaping(message, new_message):
    user = user_info('user', None, None)
    channel = '#channel'

    plugin = SedPlugin()
    plugin.history[channel][user] = 'hi/hey/hello'

    assert plugin.substitute(user, channel, message) == new_message


def test_not_a_substitute():
    user = user_info('user', None, None)
    channel = '#channel'

    plugin = SedPlugin()
    plugin.history[channel][user] = 'doesnt matter'

    assert plugin.substitute(user, channel, 'foobar') == None


def test_on_quit():
    channel = '#channel'
    nick = 'nick'
    msg = 'msg'

    plugin = SedPlugin()
    cardinal = Mock()

    plugin.on_msg(cardinal, user_info(nick, None, None), channel, msg)
    assert plugin.history[channel] == {
        nick: msg
    }

    plugin.on_quit(cardinal, nick, 'message')
    assert plugin.history[channel] == {}


def test_on_quit():
    channel = '#channel'

    plugin = SedPlugin()
    assert plugin.history[channel] == {}
    cardinal = Mock()

    # make sure this doesn't raise
    plugin.on_quit(cardinal, 'quitter', 'message')
    assert plugin.history[channel] == {}
