import pytest
from unittest.mock import Mock

from cardinal.bot import CardinalBot
from plugins.crypto.plugin import CryptoPlugin


def make_coin(slug='bitcoin'):
    coin = {
        'name': 'Bitcoin',
        'symbol': 'BTC',
        'cmc_rank': 1,
        'quote': {
            'USD': {
                'price': 64000.0,
                'percent_change_24h': 1.5,
                'market_cap': 1.26e12,
            },
        },
    }
    if slug is not None:
        coin['slug'] = slug

    return coin


class TestCryptoPlugin:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        self.api_key = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        self.mock_cardinal = Mock(spec=CardinalBot)

    def make_plugin(self, **config):
        config.setdefault('cmc_api_key', self.api_key)
        plugin = CryptoPlugin(self.mock_cardinal, config)

        # __init__ schedules the first ticker; cancel it so the reactor is
        # left clean between tests
        plugin.close(self.mock_cardinal)

        return plugin

    def test_config_defaults(self):
        plugin = self.make_plugin()
        assert plugin.config['shorten_links'] is False

    def test_missing_api_key(self):
        with pytest.raises(KeyError):
            CryptoPlugin(self.mock_cardinal, {})

    def test_coin_url(self):
        plugin = self.make_plugin()
        assert plugin.coin_url(make_coin()) == \
            'https://coinmarketcap.com/currencies/bitcoin/'

    def test_coin_url_shortened(self):
        plugin = self.make_plugin(shorten_links=True)
        assert plugin.coin_url(make_coin()) == 'https://prce.cc/c/BTC'

    def test_coin_url_missing_slug(self):
        plugin = self.make_plugin()
        assert plugin.coin_url(make_coin(slug=None)) is None

    def test_coin_url_shortened_missing_slug(self):
        """The shortener redirects by symbol, so the slug is irrelevant"""
        plugin = self.make_plugin(shorten_links=True)
        assert plugin.coin_url(make_coin(slug=None)) == 'https://prce.cc/c/BTC'

    def test_format_coin_messages_appends_url(self):
        plugin = self.make_plugin(shorten_links=True)
        messages = plugin.format_coin_messages(make_coin())
        assert len(messages) == 1
        assert messages[0].endswith(' - https://prce.cc/c/BTC')

    def test_format_coin_messages_omits_unbuildable_url(self):
        plugin = self.make_plugin()
        messages = plugin.format_coin_messages(make_coin(slug=None))
        assert len(messages) == 1
        assert messages[0].endswith('Ranked #1)')
