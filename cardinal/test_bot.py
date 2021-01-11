from builtins import object
import logging
import os
import shutil
import signal
import tempfile
from contextlib import contextmanager
from datetime import datetime

import pytest
from mock import Mock, call, patch
from twisted.internet import defer
from twisted.internet.task import Clock
from twisted.words.protocols.irc import ServerSupportedFeatures

from cardinal import exceptions, plugins
from cardinal.bot import (
    CardinalBot,
    CardinalBotFactory,
    user_info,
)


@contextmanager
def tempdir(name):
    tempdir_path = os.path.join(tempfile.gettempdir(), name)
    os.mkdir(tempdir_path)
    try:
        yield tempdir_path
    finally:
        shutil.rmtree(tempdir_path)


class TestCardinalBot(object):
    @patch('cardinal.bot.EventManager', autospec=True)
    def setup_method(self, method, mock_event_manager):
        self.cardinal = CardinalBot()
        mock_event_manager.assert_called_once_with(self.cardinal)

        self.factory = self.cardinal.factory = Mock(spec=CardinalBotFactory)
        self.factory.nickname = 'Cardinal'
        self.factory.username = 'cardinal'
        self.factory.realname = 'Cardinal'
        self.factory.password = None
        self.factory.network = 'irc.darkscience.net'
        self.factory.server_password = None
        self.factory.server_commands = []
        self.factory.channels = []
        self.factory.plugins = []
        self.factory.blacklist = {}
        self.factory.booted = datetime.now()
        self.factory.storage_path = '.'

        self.event_manager = mock_event_manager.return_value

        self.plugin_manager = self.cardinal.plugin_manager = \
            Mock(spec=plugins.PluginManager)

        # Some built-in Twisted methods will check self.supported, which is
        # typically setup during connectionMade(). That method won't get called
        # in testing.
        self.cardinal.supported = ServerSupportedFeatures()

    @staticmethod
    def get_user():
        user = user_info('nick', 'user', 'vhost')
        return "{}!{}@{}".format(user.nick, user.user, user.vhost), user

    def test_constructor(self):
        assert isinstance(self.cardinal.logger, logging.Logger)
        assert isinstance(self.cardinal.irc_logger, logging.Logger)

        # Should setup EventManager with IRC events
        assert self.event_manager.register.mock_calls == [
            call("irc.raw", 2),
            call("irc.invite", 2),
            call("irc.privmsg", 3),
            call("irc.notice", 3),
            call("irc.nick", 2),
            call("irc.mode", 3),
            call("irc.topic", 3),
            call("irc.join", 2),
            call("irc.part", 3),
            call("irc.kick", 4),
            call("irc.quit", 2),
        ]

        assert self.cardinal._who_cache == {}
        assert self.cardinal._who_deferreds == {}

    def test_factory_pass_thru_properties(self):
        assert self.cardinal.network == self.factory.network

        self.cardinal.network = 'irc.freenode.net'
        assert self.factory.network == 'irc.freenode.net'

        assert self.cardinal.nickname == self.factory.nickname
        self.cardinal.nickname = 'NotCardinal'
        assert self.factory.nickname == 'NotCardinal'

        assert self.cardinal.password == self.factory.server_password
        self.cardinal.password = 'server_password'
        assert self.factory.server_password == 'server_password'

        assert self.cardinal.username == self.factory.username
        self.cardinal.username = 'username'
        assert self.factory.username == 'username'

        assert self.cardinal.realname == self.factory.realname
        self.cardinal.realname = 'realname'
        assert self.factory.realname == 'realname'

        assert self.cardinal.storage_path == self.factory.storage_path
        with pytest.raises(AttributeError):
            self.cardinal.storage_path = '/path/to/storage'

    @patch.object(CardinalBot, 'join')
    @patch.object(CardinalBot, 'msg')
    @patch.object(CardinalBot, 'send')
    @patch('cardinal.bot.PluginManager', autospec=True)
    def test_signedOn_sets_bot_mode_joins_and_instantiates_plugin_manager(
            self,
            mock_plugin_manager,
            mock_send,
            mock_msg,
            mock_join,
    ):
        # we want to make sure this is created
        del self.cardinal.plugin_manager

        channels = ['#channel1', '#channel2']
        self.factory.channels = channels

        self.cardinal.signedOn()

        assert not mock_msg.called  # no nickserv password provided
        assert mock_join.mock_calls == [call(channel) for channel in channels]
        mock_send.assert_called_once_with("MODE {} +B".format(
            self.cardinal.nickname
        ))

        mock_plugin_manager.assert_called_once_with(self.cardinal,
                                                    self.factory.plugins,
                                                    self.factory.blacklist)
        assert isinstance(self.cardinal.plugin_manager, plugins.PluginManager)

        assert isinstance(self.cardinal.uptime, datetime)
        assert self.cardinal.booted == self.factory.booted

    @patch.object(CardinalBot, 'join')
    @patch.object(CardinalBot, 'msg')
    @patch.object(CardinalBot, 'send')
    @patch('cardinal.bot.PluginManager', autospec=True)
    def test_signedOn_messages_nickserv(
            self,
            mock_plugin_manager,
            _mock_send,
            mock_msg,
            mock_join,
    ):
        self.factory.password = 'password'

        self.cardinal.signedOn()

        assert not mock_join.called
        mock_msg.assert_called_once_with(
            'NickServ',
            'IDENTIFY {}'.format(self.factory.password)
        )

    @patch.object(CardinalBot, 'msg')
    @patch.object(CardinalBot, 'send')
    @patch('cardinal.bot.PluginManager', autospec=True)
    def test_signedOn_sends_server_commands(
            self,
            mock_plugin_manager,
            mock_send,
            _mock_msg,
    ):
        command1 = 'AUTH foobar'
        command2 = 'PING'

        self.factory.server_commands = [
            command1,
            command2,
        ]

        self.cardinal.signedOn()

        mock_send.assert_has_calls([
            call(command1),
            call(command2),
            call('MODE {} +B'.format(self.factory.nickname))
        ])

    @patch('cardinal.bot.irc.IRCClient.lineReceived')
    def test_lineReceived(self, mock_parent_linereceived):
        line = b':irc.example.com TEST :foobar foobar'
        self.cardinal.lineReceived(line)
        self.event_manager.fire.assert_called_once_with(
            'irc.raw',
            'TEST',
            ':irc.example.com TEST :foobar foobar'
        )
        mock_parent_linereceived.assert_called_once_with(line)

    @patch('cardinal.bot.irc.IRCClient.lineReceived')
    def test_lineReceived_non_utf8(self, mock_parent_linereceived):
        line = b":irc-us-east-2.darkscience.net 332 Cardinal #pirates :\x031 \x0311,10[\x031]\x031,1\x1f\xc3\x82\xc2\xaf\x1f\x0313,6[\x031]\x031,1\x1f\xc3\x82\xc2\xaf\x1f\x0311,10[\x031]\x031,1\x1f\xc3\x82\xc2\xaf\x1f\x0313,6[\x031]\x031,1\x1f\xc3\x82\xc2\xaf\x1f\x0311,10[\x031]\x031,1\x1f\xc3\x82\xc2\xaf\x1f\x0313,6[\x031]\x031,1\x1f\xc3\x82\xc2\xaf\x1f\x0311,10[\x031]\x03\x0311,6\x030 Pirates Game! - Welcome aboard Dark Sails, Season 4, Mod: Pauper Privateers! - \x1dJoin wit\' !Pirates\x1d - \x0311\x1fwww.piratesirc.com\x1f \x0311,6\x0311,10[\x031]\x031,1\x1f\xc3\x82\xc2\xaf\x1f\x0313,6[\x031]\x031,1\x1f\xc3\x82\xc2"  # noqa: E501
        expected_line = line.decode('utf-8', 'replace')

        self.cardinal.lineReceived(line)

        self.event_manager.fire.assert_called_once_with(
            'irc.raw',
            '332',
            expected_line,
        )
        mock_parent_linereceived.assert_called_once_with(
                expected_line.encode('utf-8', 'replace'))

    def test_irc_PRIVMSG(self):
        self.plugin_manager.call_command.side_effect = \
            exceptions.CommandNotFoundError  # should be caught

        prefix, source = self.get_user()
        channel = '#test'
        message = 'this is a test'

        self.cardinal.irc_PRIVMSG(prefix, [channel, message])

        self.event_manager.fire.assert_called_once_with(
            'irc.privmsg',
            source,
            '#test',
            'this is a test',
        )

        self.plugin_manager.call_command.assert_called_once_with(
            source,
            channel,
            message,
        )

    def test_irc_PRIVMSG_in_private_chat(self):
        self.plugin_manager.call_command.side_effect = \
            exceptions.CommandNotFoundError  # should be caught

        prefix, source = self.get_user()
        channel = self.cardinal.nickname
        message = 'this is a test'

        self.cardinal.irc_PRIVMSG(prefix,
                                  [channel, message])

        self.event_manager.fire.assert_called_once_with(
            'irc.privmsg',
            source,
            channel,
            'this is a test',
        )

        self.plugin_manager.call_command.assert_called_once_with(
            source,
            source.nick,
            message,
        )

    def test_irc_NOTICE(self):
        prefix, source = self.get_user()
        channel = '#test'
        message = 'this is a test'

        self.cardinal.irc_NOTICE(prefix, [channel, message])

        self.event_manager.fire.assert_called_once_with(
            'irc.notice',
            source,
            '#test',
            'this is a test',
        )

    def test_irc_NOTICE_from_server_no_events(self):
        channel = self.factory.nickname
        message = 'this is a test'

        self.cardinal.irc_NOTICE('irc.freenode.net',
                                 [channel, message])

        assert not self.event_manager.fire.called

    def test_irc_NICK(self):
        prefix, source = self.get_user()
        new_nick = 'new_nick'

        self.cardinal.irc_NICK(prefix, [new_nick])

        self.event_manager.fire.assert_called_once_with(
            'irc.nick',
            source,
            new_nick,
        )

    def test_irc_TOPIC(self):
        prefix, source = self.get_user()
        channel = '#channel'
        topic = 'New topic'

        self.cardinal.irc_TOPIC(prefix, [channel, topic])

        self.event_manager.fire.assert_called_once_with(
            'irc.topic',
            source,
            channel,
            topic,
        )

    def test_irc_MODE(self):
        prefix, source = self.get_user()
        channel = '#channel'

        self.cardinal.irc_MODE(prefix, [channel, '+b', 'user!*@*'])

        self.event_manager.fire.assert_called_once_with(
            'irc.mode',
            source,
            channel,
            '+b user!*@*',
        )

    def test_irc_MODE_from_server_no_events(self):
        channel = '#channel'

        self.cardinal.irc_MODE('irc.freenode.net',
                               [channel, '+b', 'user!*@*'])

        assert not self.event_manager.fire.called

    def test_irc_JOIN(self):
        prefix, source = self.get_user()
        channel = '#channel'

        self.cardinal.irc_JOIN(prefix, [channel])

        self.event_manager.fire.assert_called_once_with(
            'irc.join',
            source,
            channel,
        )

    def test_irc_PART(self):
        prefix, source = self.get_user()
        channel = '#channel'
        message = 'Leaving the channel now'

        self.cardinal.irc_PART(prefix, [channel, message])

        self.event_manager.fire.assert_called_once_with(
            'irc.part',
            source,
            channel,
            message,
        )

    def test_irc_PART_no_message(self):
        prefix, source = self.get_user()
        channel = '#channel'

        self.cardinal.irc_PART(prefix, [channel])

        self.event_manager.fire.assert_called_once_with(
            'irc.part',
            source,
            channel,
            None,
        )

    def test_irc_KICK(self):
        prefix, source = self.get_user()
        nick = 'kicked_nick'
        channel = '#channel'
        message = 'And stay out!'

        self.cardinal.irc_KICK(prefix, [channel, nick, message])

        self.event_manager.fire.assert_called_once_with(
            'irc.kick',
            source,
            channel,
            nick,
            message,
        )

    def test_irc_KICK_no_message(self):
        prefix, source = self.get_user()
        nick = 'kicked_nick'
        channel = '#channel'

        self.cardinal.irc_KICK(prefix, [channel, nick])

        self.event_manager.fire.assert_called_once_with(
            'irc.kick',
            source,
            channel,
            nick,
            None,
        )

    def test_irc_QUIT(self):
        prefix, source = self.get_user()
        message = "Goodbye now!"

        self.cardinal.irc_QUIT(prefix, [message])

        self.event_manager.fire.assert_called_once_with(
            'irc.quit',
            source,
            message,
        )

    def test_irc_unknown_no_op(self):
        prefix, _ = self.get_user()
        self.cardinal.irc_unknown(prefix, 'UNKNOWN', [])
        assert not self.event_manager.fire.called

    def test_irc_unknown_handles_INVITE(self):
        prefix, user = self.get_user()
        channel = '#channel'

        self.cardinal.irc_unknown(prefix, 'INVITE', ['Cardinal', channel])

        self.event_manager.fire.assert_called_once_with(
            'irc.invite', user, channel)

    @defer.inlineCallbacks
    def test_who(self):
        _, user = self.get_user()
        channel = '#channel'

        # Issue WHO to server
        with patch.object(self.cardinal, 'sendLine'):
            d = self.cardinal.who(channel)
        assert isinstance(d, defer.Deferred)

        # Simulate another plugin separately issuing WHO
        with patch.object(self.cardinal, 'sendLine'):
            d2 = self.cardinal.who(channel)

        # Need separate Deferreds to prevent each callback needing to return
        # the results, and prevent an error in one callback from breaking
        # another
        assert d is not d2

        self.cardinal.irc_RPL_WHOREPLY('irc.freenode.net', [
            'Cardinal',  # nick requesting WHO
            channel,  # channel WHO refers to
            user.user,  # username/ident
            user.vhost,  # user hostname
            'celadon.darkscience.net',  # server connected to
            user.nick,  # nickserv namea
            'H',  # H = here, G = gone, * suffix = IRC Operator
            '0 Mr. Cardinal',  # 0 = number of servers between you and user,
                               # then space precedes realname
        ])

        self.cardinal.irc_RPL_ENDOFWHO('irc.freenode.net', [
            'Cardinal', channel, 'End of /WHO list.'
        ])

        users = yield d
        assert users == [user]

        users2 = yield d2
        assert users == users2

    def test_config_raises_without_plugin_manager(self):
        self.cardinal.plugin_manager = None
        with pytest.raises(exceptions.PluginError):
            self.cardinal.config('plugin')

    def test_config_raises_for_config_not_found(self):
        plugin_name = 'plugin'

        self.plugin_manager.get_config.side_effect = \
            exceptions.ConfigNotFoundError
        with pytest.raises(exceptions.ConfigNotFoundError):
            self.cardinal.config(plugin_name)

        self.plugin_manager.get_config.assert_called_once_with(plugin_name)

    def test_config(self):
        plugin_name = 'plugin'

        return_value = {}
        self.plugin_manager.get_config.return_value = return_value
        assert self.cardinal.config(plugin_name) == return_value

        self.plugin_manager.get_config.assert_called_once_with(plugin_name)

    def test_sendMsg(self):
        # passes through to Twisted w/ additional logging
        channel = '#channel'
        message = 'this is some message'
        length = 5

        with patch.object(self.cardinal, 'msg') as msg_mock:
            self.cardinal.sendMsg(channel, message, length)

        msg_mock.assert_called_once_with(channel, message, length)

    def test_sendMsg_no_length(self):
        # passes through to Twisted w/ additional logging
        channel = '#channel'
        message = 'this is some message'

        with patch.object(self.cardinal, 'msg') as msg_mock:
            self.cardinal.sendMsg(channel, message)

        msg_mock.assert_called_once_with(channel, message, None)

    def test_send(self):
        # passes through to Twisted w/ additional logging
        message = 'PRIVMSG #channel :this is a message'

        with patch.object(self.cardinal, 'sendLine') as sendLine_mock:
            self.cardinal.send(message)

        sendLine_mock.assert_called_once_with(message)

    def test_disconnect(self):
        with patch.object(self.cardinal, 'quit') as quit_mock:
            self.cardinal.disconnect()

        self.plugin_manager.unload_all.assert_called_once_with()
        assert self.factory.disconnect is True
        quit_mock.assert_called_once_with('')

    def test_disconnect_with_message(self):
        message = 'Quitting now'

        with patch.object(self.cardinal, 'quit') as quit_mock:
            self.cardinal.disconnect(message)

        self.plugin_manager.unload_all.assert_called_once_with()
        assert self.factory.disconnect is True
        quit_mock.assert_called_once_with(message)

    def test_get_db(self):
        assert self.cardinal.db_locks == {}

        with tempdir('database') as database_path:
            self.factory.storage_path = os.path.dirname(database_path)

            db = self.cardinal.get_db('test')

        assert len(self.cardinal.db_locks) == 1
        db_path = list(self.cardinal.db_locks.keys())[0]
        assert db_path.endswith(os.path.join(
            'database', 'test-{}.json'.format(self.factory.network)))

        assert callable(db)

    def test_get_db_not_network_specific(self):
        with tempdir('database') as database_path:
            self.factory.storage_path = os.path.dirname(database_path)

            self.cardinal.get_db('test', network_specific=False)

        assert len(self.cardinal.db_locks) == 1
        db_path = list(self.cardinal.db_locks.keys())[0]
        # note lack of network formatted in below
        assert db_path.endswith(os.path.join(
            'database', 'test.json'))

    def test_get_db_db(self):
        with tempdir('database') as database_path:
            self.factory.storage_path = os.path.dirname(database_path)
            db = self.cardinal.get_db('test', network_specific=False)

            with db() as db1:
                assert db1 == {}
                db1['test'] = 'x'

            with db() as db2:
                assert db1 == db2

    def test_db_contextmanager_locks(self):
        with tempdir('database') as database_path:
            self.factory.storage_path = os.path.dirname(database_path)
            db = self.cardinal.get_db('test', network_specific=False)

            with db():
                with pytest.raises(exceptions.LockInUseError):
                    with db():
                        pass

    def test_db_contextmanager_locks_with_multiple_get_db_calls(self):
        with tempdir('database') as database_path:
            self.factory.storage_path = os.path.dirname(database_path)
            db1 = self.cardinal.get_db('test', network_specific=False)
            db2 = self.cardinal.get_db('test', network_specific=False)

            with db1():
                with pytest.raises(exceptions.LockInUseError):
                    with db2():
                        pass

    def test_db_contextmanager_exception(self):
        with tempdir('database') as database_path:
            self.factory.storage_path = os.path.dirname(database_path)
            db = self.cardinal.get_db('test', network_specific=False)

            try:
                with db() as db_obj:
                    assert db_obj == {}
                    db_obj['x'] = True
                    raise Exception()
            except Exception:
                pass

            with db() as db_obj:
                assert db_obj == {}

    def test_get_user_tuple(self):
        assert CardinalBot.get_user_tuple('unit|test!unit~@unit/test') == \
            ('unit|test', 'unit~', 'unit/test')

    def test_get_user_tuple_names(self):
        user = CardinalBot.get_user_tuple('unittest!unit@unit.test')
        assert user.nick == 'unittest'
        assert user.user == 'unit'
        assert user.vhost == 'unit.test'

    def test_get_user_tuple_doesnt_match(self):
        assert CardinalBot.get_user_tuple('foobar') is None


class TestCardinalBotFactory(object):
    def setup_method(self):
        self.factory = CardinalBotFactory(
            network='irc.testnet.test',
            server_password='s3rv3r_p4ssw0rd',
            server_commands=['AUTH password', 'MODE +b foobar'],
            channels=['#channel1', '#channel2'],
            nickname='Cardinal|unit-test',
            password='p4ssw0rd',
            username='cardinal',
            realname='Mr. Cardinal',
            plugins=['plugin1', 'plugin2'],
            blacklist=[
                {'urls': '#finance'},
            ],
            storage='/path/to/storage',
        )

    def teardown_method(self, method):
        # remove signal handler set by the factory
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        del self.factory

    def test_class_properties(self):
        assert CardinalBotFactory.protocol is CardinalBot
        assert CardinalBotFactory.MINIMUM_RECONNECTION_WAIT == 10
        assert CardinalBotFactory.MAXIMUM_RECONNECTION_WAIT == 300

    def test_constructor(self):
        network = 'IrC.TeStNeT.TeSt'
        server_password = 's3rv3r_p4ssw0rd'
        server_commands = ['AUTH password', 'MODE +b foobar']
        channels = ['#channel1', '#channel2']
        nickname = 'Cardinal|unit-test'
        password = 'p4ssw0rd'
        username = 'cardinal'
        realname = 'Mr. Cardinal'
        plugins = ['plugin1', 'plugin2']
        blacklist = [
            {'urls': '#finance'},
        ]
        storage = '/path/to/storage'

        factory = CardinalBotFactory(
            network,
            server_password,
            server_commands,
            channels,
            nickname,
            password,
            username,
            realname,
            plugins,
            blacklist,
            storage,
        )

        assert isinstance(factory.logger, logging.Logger)

        # Check that signal handler got registered
        assert signal.getsignal(signal.SIGINT) == factory._sigint

        # Defaults that aren't passed in
        assert self.factory.cardinal is None
        assert self.factory.disconnect is False
        assert isinstance(self.factory.booted, datetime)
        assert self.factory.last_reconnection_wait is None

        assert factory.network == network.lower()
        assert factory.server_commands == server_commands
        assert factory.server_password == server_password
        assert factory.password == password
        assert factory.channels == channels
        assert factory.nickname == nickname
        assert factory.username == username
        assert factory.realname == realname
        assert factory.plugins == plugins
        assert factory.blacklist == blacklist
        assert factory.storage_path == storage

    def test_sigint_handler(self):
        mock_cardinal = Mock(spec=CardinalBot)
        self.factory.cardinal = mock_cardinal

        assert self.factory.disconnect is False

        os.kill(os.getpid(), signal.SIGINT)

        assert self.factory.disconnect is True
        mock_cardinal.quit.assert_called_once_with('Received SIGINT.')

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
