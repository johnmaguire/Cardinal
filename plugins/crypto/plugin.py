import logging
import re
from datetime import datetime, timezone

import requests
from twisted.internet import defer, error, reactor
from twisted.internet.threads import deferToThread

from cardinal import util
from cardinal.bot import user_info
from cardinal.decorators import command, regex, help
from cardinal.util import F

# CoinMarketCap API Endpoint
CMC_QUOTE_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"  # noqa: E501

# Regex pattern that matches PyLink relay bots
RELAY_REGEX = r'^(?:(?:\[.+\] )?<(.+?)>\s+)'

# For 'crypto' command - checking cryptocurrency price
CRYPTO_REGEX = RELAY_REGEX + r'(\.crypto.*?)$'

# Max simultaneous cryptocurrency results
MAX_LOOKUPS = 5


def colorize(percentage):
    message = '{:.2f}%'.format(percentage)
    if percentage > 0:
        return F.C.light_green(message)
    else:
        return F.C.light_red(message)


class CMCError(Exception):
    """Represents a CoinMarketCap error"""
    pass


class CryptoPlugin:
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)
        self.cardinal = cardinal

        self.config = config or {}
        self.config.setdefault('cmc_api_key', None)
        self.config.setdefault('default_crypto_price_currency', 'USD')
        self.config.setdefault('relay_bots', [])
        self.config.setdefault('ticker_channels', [])
        self.config.setdefault('ticker_coins', ['BTC'])

        if not self.config["cmc_api_key"]:
            raise KeyError(
                "Missing cmc_api_key (CoinMarketCap) - crypto functions will "
                "be unavailable")

        self.relay_bots = []
        for relay_bot in self.config['relay_bots']:
            user = user_info(
                relay_bot['nick'],
                relay_bot['user'],
                relay_bot['vhost'])
            self.relay_bots.append(user)

        self.call_id = None
        self.wait()

    def wait(self):
        """Tell the reactor to call tick() at the next 6-hour UTC boundary"""
        now = datetime.now(timezone.utc)
        seconds_into_period = (now.hour % 6) * 3600 + \
            now.minute * 60 + now.second
        self.call_id = reactor.callLater(
            6 * 3600 - seconds_into_period, self.tick)

    def close(self, cardinal):
        if self.call_id:
            try:
                self.call_id.cancel()
            except error.AlreadyCancelled as e:
                self.logger.debug(e)

    @defer.inlineCallbacks
    def tick(self):
        """Send the coin ticker to configured channels (4x daily)"""
        # Schedule the next tick first: if the plugin is reloaded while the
        # request below is in flight, close() must be able to cancel the
        # pending call so the old instance stops ticking.
        self.wait()

        if not self.config['ticker_channels']:
            return

        coin = ','.join(self.config['ticker_coins'])
        currency = self.config['default_crypto_price_currency']
        try:
            resp = yield self.make_cmc_request(coin, currency)
        except Exception as exc:
            self.logger.warning(
                "Error fetching ticker for {} in currency {}: {}"
                .format(coin, currency, exc))
            return

        for coin in resp.values():
            for message in self.format_coin_messages(coin):
                for channel in self.config['ticker_channels']:
                    self.cardinal.sendMsg(channel, message)

    @command('crypto')
    @help('Check the price of a cryptocurrency')
    @help('Syntax: .crypto <cryptocurrency,...> [price currency]')
    @defer.inlineCallbacks
    def crypto(self, cardinal, user, channel, message):
        nick = user.nick

        try:
            parts = message.split(' ', 2)
            coin = parts[1]
        except IndexError:
            cardinal.sendMsg(
                channel, "Syntax: .crypto <cryptocurrency> [price currency]")
            return

        if len(coin.split(',')) > MAX_LOOKUPS:
            cardinal.sendMsg(
                channel, "Please request no more than {} coins at once".format(
                    MAX_LOOKUPS))
            return

        try:
            currency = parts[2]
        except IndexError:
            currency = self.config['default_crypto_price_currency']

        try:
            resp = yield self.make_cmc_request(coin, currency)
        except CMCError as e:
            self.logger.warning(e)

            # Probably safe to send?
            cardinal.sendMsg(
                channel, "{}".format(e))
            return
        except Exception as exc:
            self.logger.warning(
                "Error trying to look up coin {} in currency {}: {}"
                .format(coin, currency, exc))
            cardinal.sendMsg(
                channel, "{}: I couldn't look that coin up".format(nick))
            return

        for coin in resp.values():
            for message in self.format_coin_messages(coin):
                cardinal.sendMsg(channel, message)

    def format_coin_messages(self, coin):
        """Format a CMC coin record as one message per quote currency"""
        messages = []
        for quote_currency, quote in coin['quote'].items():
            price = quote['price']
            if price >= 1:
                price = round(price, 2)
            else:
                price = float("%.4g" % price)

            messages.append(
                "{} ({}) = {:,.2f} {} - Daily Change (24h): {} "
                "(Market Cap: {} - Ranked #{})".format(
                    coin['name'], F.bold(coin['symbol']),
                    price, quote_currency,
                    colorize(quote['percent_change_24h']),
                    self.format_market_cap(quote['market_cap']),
                    coin['cmc_rank']))

        return messages

    @regex(CRYPTO_REGEX)
    @defer.inlineCallbacks
    def crypto_regex(self, cardinal, user, channel, message):
        """Hack to support relayed messages"""
        match = re.match(CRYPTO_REGEX, message)

        # this group should only be present when a relay bot is relaying a
        # message for another user
        if not match.group(1):
            return
        if not self.is_relay_bot(user):
            return

        user = user_info(util.strip_formatting(match.group(1)),
                         user.user,
                         user.vhost,
                         )

        yield self.crypto(cardinal, user, channel, match.group(2))

    @defer.inlineCallbacks
    def make_cmc_request(self, coin, currency):
        r = yield deferToThread(requests.get, CMC_QUOTE_API_URL, params={
            'convert': currency,
            'symbol': coin,
        }, headers={
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.config['cmc_api_key'],
        })

        resp = r.json()
        if resp['status']['error_code']:
            raise CMCError(
                "CoinMarketCap gave error {error_code}: {error_message}"
                .format(
                    error_code=resp['status']['error_code'],
                    error_message=resp['status']['error_message'],
                ))

        return resp['data']

    def is_relay_bot(self, user):
        """Compares a user against the registered relay bots."""
        for bot in self.relay_bots:
            if (bot.nick is None or bot.nick == user.nick) and \
                    (bot.user is None or bot.user == user.user) and \
                    (bot.vhost is None or bot.vhost == user.vhost):
                return True

        return False

    def format_market_cap(self, value):
        """Format market cap with appropriate suffix (T, B, M, K)"""
        abs_value = abs(value)
        if abs_value >= 1e12:
            return "${:.3f}T".format(value / 1e12)
        elif abs_value >= 1e9:
            return "${:.3f}B".format(value / 1e9)
        elif abs_value >= 1e6:
            return "${:.3f}M".format(value / 1e6)
        elif abs_value >= 1e3:
            return "${:.3f}K".format(value / 1e3)
        else:
            return "${:.2f}".format(value)



entrypoint = CryptoPlugin
