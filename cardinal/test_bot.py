import logging
import os
import signal
from datetime import datetime

from mock import Mock, patch
from twisted.internet.task import Clock

from cardinal.bot import CardinalBot, CardinalBotFactory


class MockCardinal(object):
    """Used for testing various Factory methods"""
    def __init__(self):
        self.quit_called = False
        self.quit_message = None

    def quit(self, message):
        self.quit_called = True
        self.quit_message = message


class TestCardinalBotFactory(object):
    def setup_method(self, method):
        self.factory = CardinalBotFactory(
            network='irc.TestNet.test'
        )

    def teardown_method(self, method):
        # remove signal handler set by the factory
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        del self.factory

    def test_class_properties(self):
        assert CardinalBotFactory.protocol is CardinalBot
        assert CardinalBotFactory.MINIMUM_RECONNECTION_WAIT == 10
        assert CardinalBotFactory.MAXIMUM_RECONNECTION_WAIT == 300

    def test_constructor_args_defaults(self):
        assert isinstance(self.factory.logger, logging.Logger)

        assert self.factory.network == 'irc.testnet.test'
        assert self.factory.server_password is None
        assert self.factory.password is None
        assert self.factory.channels == []
        assert self.factory.nickname == 'Cardinal'
        assert self.factory.username is None
        assert self.factory.realname is None
        assert self.factory.plugins == []
        assert self.factory.storage_path is None

        # Check that signal handler got registered
        assert signal.getsignal(signal.SIGINT) == self.factory._sigint

        # Defaults that aren't passed in
        assert self.factory.cardinal is None
        assert self.factory.disconnect is False
        assert isinstance(self.factory.booted, datetime)
        assert self.factory.reloads == 0
        assert self.factory.last_reconnection_wait is None

    def test_constructor_args_non_default(self):
        server_password = 's3rv3r_p4ssw0rd'
        channels = ['#channel1', '#channel2']
        nickname = 'Cardinal|unit-test'
        password = 'p4ssw0rd'
        username = 'cardinal'
        realname = 'Mr. Cardinal'
        plugins = ['plugin1', 'plugin2']
        storage = '/path/to/storage'

        factory = CardinalBotFactory(
            'IrC.TeStNeT.TeSt',
            server_password,
            channels,
            nickname,
            password,
            username,
            realname,
            plugins,
            storage,
        )

        assert factory.network == 'irc.testnet.test'
        assert factory.server_password == server_password
        assert factory.password == password
        assert factory.channels == channels
        assert factory.nickname == nickname
        assert factory.username == username
        assert factory.realname == realname
        assert factory.plugins == plugins
        assert factory.storage_path == storage

    def test_sigint_handler(self):
        cardinal = MockCardinal()
        self.factory.cardinal = cardinal

        assert self.factory.disconnect is False

        os.kill(os.getpid(), signal.SIGINT)

        assert self.factory.disconnect is True
        assert cardinal.quit_called is True
        assert cardinal.quit_message == 'Received SIGINT.'

    def test_sigint_handler_without_cardinal(self):
        assert self.factory.disconnect is False

        os.kill(os.getpid(), signal.SIGINT)

        assert self.factory.disconnect is True

    def test_reconnection(self):
        assert self.factory.disconnect is False

        clock = Clock()
        mock_connector = Mock()
        self.factory._reactor = clock

        self.factory.clientConnectionLost(
            mock_connector,
            'Called by unit test'
        )

        assert self.factory.last_reconnection_wait == \
            CardinalBotFactory.MINIMUM_RECONNECTION_WAIT
        clock.advance(self.factory.last_reconnection_wait)

        mock_connector.connect.assert_called_once()

    def test_initial_connection_failed(self):
        assert self.factory.disconnect is False
        assert self.factory.last_reconnection_wait is None

        clock = Clock()
        mock_connector = Mock()
        self.factory._reactor = clock

        self.factory.clientConnectionFailed(
            mock_connector,
            'Called by unit test'
        )

        assert self.factory.last_reconnection_wait == \
            CardinalBotFactory.MINIMUM_RECONNECTION_WAIT
        clock.advance(self.factory.last_reconnection_wait)

        mock_connector.connect.assert_called_once()

    def test_reconnection_failed(self):
        assert self.factory.disconnect is False
        self.factory.last_reconnection_wait = \
            CardinalBotFactory.MINIMUM_RECONNECTION_WAIT

        clock = Clock()
        mock_connector = Mock()
        self.factory._reactor = clock

        self.factory.clientConnectionFailed(
            mock_connector,
            'Called by unit test'
        )

        # time should have doubled
        assert self.factory.last_reconnection_wait == \
            CardinalBotFactory.MINIMUM_RECONNECTION_WAIT * 2

        # make sure it's not called on original time
        clock.advance(self.factory.MINIMUM_RECONNECTION_WAIT)
        assert not mock_connector.connect.called

        # advance it one more time and it should be
        clock.advance(self.factory.MINIMUM_RECONNECTION_WAIT)
        mock_connector.connect.assert_called_once()

    def test_reconnection_failed_max_wait(self):
        assert self.factory.disconnect is False
        self.factory.last_reconnection_wait = \
            CardinalBotFactory.MAXIMUM_RECONNECTION_WAIT

        clock = Clock()
        mock_connector = Mock()
        self.factory._reactor = clock

        self.factory.clientConnectionFailed(
            mock_connector,
            'Called by unit test'
        )

        # cannot increase past maximum
        assert self.factory.last_reconnection_wait == \
            CardinalBotFactory.MAXIMUM_RECONNECTION_WAIT

        # advance it one more time and it should be
        clock.advance(self.factory.MAXIMUM_RECONNECTION_WAIT)
        mock_connector.connect.assert_called_once()

    def test_bypass_reconnection(self):
        # Mark that we purposefully disconnected
        self.factory.disconnect = True

        self.factory._reactor = Mock()

        self.factory.clientConnectionLost(None, 'Called by unit test')

        self.factory._reactor.stop.assert_called_once()
