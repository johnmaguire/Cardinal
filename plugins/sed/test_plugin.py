import pytest

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
