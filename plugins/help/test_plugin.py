from datetime import datetime, timedelta

from mock import Mock, PropertyMock, call, patch

from cardinal.bot import CardinalBot, user_info
from plugins.help import plugin


class TestHelpPlugin(object):
    def setup_method(self, method):
        self.mock_cardinal = Mock(spec=CardinalBot)
        self.plugin = plugin.HelpPlugin()

    @patch.object(plugin, 'datetime')
    def test_cmd_info(self, mock_datetime):
        channel = '#test'
        msg = '.info'

        now = datetime.now()
        reloads = 123
        mock_datetime.now = Mock(return_value=now)

        type(self.mock_cardinal).reloads = PropertyMock(return_value=123)
        self.mock_cardinal.booted = now - timedelta(seconds=30)
        self.mock_cardinal.uptime = now - timedelta(seconds=15)
        self.mock_cardinal.config.return_value = {
            'admins': [
                {'nick': 'whoami'},
                {'nick': 'test_foo'},
            ]
        }

        self.plugin.cmd_info(
            self.mock_cardinal,
            user_info(None, None, None),
            channel,
            msg,
        )

        assert self.mock_cardinal.sendMsg.mock_calls == [
            call(
                channel,
                "I have been connected without downtime for 00:00:15, and was "
                "initially launched 00:00:30 ago. Plugins have been reloaded "
                "123 times since then.".format(reloads),
            ),
            call(
                channel,
                "My admins are: test_foo, whoami. Visit "
                "https://github.com/JohnMaguire/Cardinal for more info about "
                "me. (Use .help to see my commands.)",
            ),
        ]
