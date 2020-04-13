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
    plugin.history[channel][user.nick] = 'this is a test message'

    assert plugin.substitute(user, channel, message) == new_message

def test_subsitution_no_history():
    user = user_info('user', None, None)
    channel = '#channel'

    plugin = SedPlugin()

    # make sure this doesn't raise
    plugin.on_msg(Mock(), user, channel, 's/foo/bar/')


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
    plugin.history[channel][user.nick] = 'hi/hey/hello'

    assert plugin.substitute(user, channel, message) == new_message


def test_not_a_substitute():
    user = user_info('user', None, None)
    channel = '#channel'

    plugin = SedPlugin()
    plugin.history[channel][user.nick] = 'doesnt matter'

    assert plugin.substitute(user, channel, 'foobar') == None


def test_on_part():
    channel1 = '#channel1'
    channel2 = '#channel2'
    user = user_info('nick', None, None)
    msg = 'msg'

    plugin = SedPlugin()
    cardinal = Mock()

    plugin.on_msg(cardinal, user, channel1, msg)
    plugin.on_msg(cardinal, user, channel2, msg)
    assert plugin.history[channel1] == {
        user.nick: msg
    }
    assert plugin.history[channel2] == {
        user.nick: msg
    }

    plugin.on_part(cardinal, user, channel1, 'message')
    assert plugin.history[channel1] == {}
    assert plugin.history[channel2] == {
        user.nick: msg
    }

    plugin.on_part(cardinal, user, channel2, 'message')
    assert plugin.history[channel2] == {}


def test_on_part_no_history():
    channel = '#channel'
    user = user_info('nick', None, None)
    msg = 'msg'

    plugin = SedPlugin()
    cardinal = Mock()

    # make sure this doesn't raise
    plugin.on_part(cardinal, user, channel, 'message')


def test_on_kick():
    channel1 = '#channel1'
    channel2 = '#channel2'
    user = user_info('nick', None, None)
    msg = 'msg'

    plugin = SedPlugin()
    cardinal = Mock()

    plugin.on_msg(cardinal, user, channel1, msg)
    plugin.on_msg(cardinal, user, channel2, msg)
    assert plugin.history[channel1] == {
        user.nick: msg
    }
    assert plugin.history[channel2] == {
        user.nick: msg
    }

    plugin.on_kick(cardinal, user, channel1, user.nick, 'message')
    assert plugin.history[channel1] == {}
    assert plugin.history[channel2] == {
        user.nick: msg
    }

    plugin.on_kick(cardinal, user, channel2, user.nick, 'message')
    assert plugin.history[channel2] == {}


def test_on_kick_no_history():
    channel = '#channel'
    user = user_info('nick', None, None)
    msg = 'msg'

    plugin = SedPlugin()
    cardinal = Mock()

    # make sure this doesn't raise
    plugin.on_kick(cardinal, user, channel, user.nick, 'message')


def test_on_quit():
    channel1 = '#channel1'
    channel2 = '#channel2'
    user = user_info('nick', None, None)
    msg = 'msg'

    plugin = SedPlugin()
    cardinal = Mock()

    plugin.on_msg(cardinal, user, channel1, msg)
    plugin.on_msg(cardinal, user, channel2, msg)
    assert plugin.history[channel1] == {
        user.nick: msg
    }
    assert plugin.history[channel2] == {
        user.nick: msg
    }

    plugin.on_quit(cardinal, user, 'message')
    assert plugin.history[channel1] == {}
    assert plugin.history[channel2] == {}


def test_on_quit_no_history():
    channel = '#channel'
    user = user_info('nick', None, None)

    plugin = SedPlugin()
    assert plugin.history[channel] == {}
    cardinal = Mock()

    # make sure this doesn't raise
    plugin.on_quit(cardinal, user, 'message')
    assert plugin.history[channel] == {}
