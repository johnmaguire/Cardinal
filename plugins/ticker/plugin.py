import datetime
import logging
import re

import pytz
import requests
from twisted.internet import defer, error, reactor
from twisted.internet.threads import deferToThread

from cardinal.bot import user_info
from cardinal.decorators import regex

# Alpha Vantage API key
AV_API_URL = "https://www.alphavantage.co/query"

CHECK_REGEX = r'^(?:<(.+?)>\s+)?!check (.+)'


def colorize(percentage):
    if percentage > 0:
        return '\x0309{:.2f}%\x03'.format(percentage)
    else:
        return '\x0304{:.2f}%\x03'.format(percentage)


class TickerPlugin(object):
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)
        self.cardinal = cardinal

        self.config = config or {}
        self.config.setdefault('api_key', None)
        self.config.setdefault('channels', [])
        self.config.setdefault('stocks', [])
        self.config.setdefault('relay_bots', [])

        if not self.config["channels"]:
            self.logger.warning("No channels for ticker defined in config --"
                                "ticker will be disabled")
        if not self.config["stocks"]:
            self.logger.warning("No stocks for ticker defined in config -- "
                                "ticker will be disabled")

        if not self.config["api_key"]:
            raise KeyError("Missing required api_key in ticker config")
        if len(self.config["stocks"]) > 5:
            raise ValueError("No more than 5 stocks may be present in ticker "
                             "config")

        self.relay_bots = []
        for relay_bot in self.config['relay_bots']:
            user = user_info(
                relay_bot['nick'],
                relay_bot['user'],
                relay_bot['vhost'])
            self.relay_bots.append(user)

        self.call_id = None
        self.wait()

    def is_relay_bot(self, user):
        """Compares a user against the registered relay bots."""
        for bot in self.relay_bots:
            if (bot.nick is None or bot.nick == user.nick) and \
                    (bot.user is None or bot.user == user.user) and \
                    (bot.vhost is None or bot.vhost == user.vhost):
                return True

        return False

    def wait(self):
        """Tell the reactor to call tick() at the next 15 minute interval"""
        now = datetime.datetime.now()
        minutes_to_sleep = 15 - now.minute % 15
        seconds_to_sleep = minutes_to_sleep * 60
        seconds_to_sleep = seconds_to_sleep - now.second

        self.call_id = reactor.callLater(minutes_to_sleep * 60, self.tick)

    @defer.inlineCallbacks
    def tick(self):
        """Send a message with daily stock movements"""
        # If it's after 4pm ET or before 9:30am ET on a weekday, or if it's
        # a weekend (Saturday or Sunday), don't tick, just wait.
        tz = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(tz)
        if (now.weekday() >= 5) or \
                (now.hour < 9 or now.hour >= 17) or \
                (now.hour == 9 and now.minute < 30) or \
                (now.hour == 16 and now.minute > 0):
            self.wait()
            return

        # If there are no stocks to send in the ticker, or no channels to send
        # them to, don't tick, just wait.
        if not self.config["channels"] or not self.config["stocks"]:
            self.wait()
            return

        try:
            results = {}
            for symbol, name in self.config["stocks"].items():
                change = yield self.get_daily_change(symbol)
                results[symbol] = colorize(change)

            messages = []
            for symbol, result in results.items():
                messages.append("{name} (\x02{symbol}\x02): {result}".format(
                    symbol=symbol,
                    name=self.config["stocks"][symbol],
                    result=result
                ))

            message = ' | '.join(messages)
            for channel in self.config["channels"]:
                self.cardinal.sendMsg(channel, message)
        except Exception as e:
            self.logger.exception("Error during tick: {}".format(e))

        self.wait()

    @regex(CHECK_REGEX)
    @defer.inlineCallbacks
    def check(self, cardinal, user, channel, msg):
        """Check a specific stock for current value and daily change"""
        nick = user.nick

        match = re.match(CHECK_REGEX, msg)
        if match.group(1):
            # this group should only be present when a relay bot is relaying a
            # message for another user
            if not self.is_relay_bot(user):
                return

            nick = match.group(1)
        symbol = match.group(2)
        try:
            data = yield self.get_daily(symbol)
        except Exception as exc:
            self.logger.warning("Error trying to look up symbol {}: {}".format(
                symbol, exc))
            cardinal.sendMsg(
                channel, "{}: Is your symbol correct?".format(nick))
            return

        cardinal.sendMsg(
            channel,
            "Symbol: \x02{}\x02 | Current: {} | Daily Change: {}".format(
                symbol,
                data['current'],
                colorize(data['percentage'])))

    def close(self, cardinal):
        if self.call_id:
            try:
                self.call_id.cancel()
            except error.AlreadyCancelled as e:
                self.logger.debug(e)

    @defer.inlineCallbacks
    def make_av_request(self, function, params=None):
        if params is None:
            params = {}
        params['function'] = function
        params['apikey'] = self.config["api_key"]
        params['datatype'] = 'json'

        r = yield deferToThread(requests.get, AV_API_URL, params=params)
        defer.returnValue(r.json())

    @defer.inlineCallbacks
    def get_time_series_daily(self, symbol, outputsize='compact'):
        data = yield self.make_av_request('TIME_SERIES_DAILY',
                                          {'symbol': symbol,
                                           'outputsize': outputsize,
                                           })
        try:
            data = data['Time Series (Daily)']
        except KeyError:
            raise Exception("Error with data: {}".format(data))

        for date, values in data.items():
            values = {k[3:]: float(v) for k, v in values.items()}
            data[date] = values

        defer.returnValue(data)

    @defer.inlineCallbacks
    def get_daily(self, symbol):
        data = yield self.get_time_series_daily(symbol)

        today = datetime.date.today()
        last_day = today - datetime.timedelta(days=1)

        while data.get(last_day.strftime('%Y-%m-%d'), None) is None:
            last_day = last_day - datetime.timedelta(days=1)

        current_value = data[today.strftime('%Y-%m-%d')]
        last_day_value = data[last_day.strftime('%Y-%m-%d')]

        percentage = (((current_value['close'] / last_day_value['close']) - 1)
                      * 100)
        defer.returnValue({'current': current_value['close'],
                           'percentage': percentage,
                           })

    @defer.inlineCallbacks
    def get_daily_change(self, symbol):
        res = yield self.get_daily(symbol)
        defer.returnValue(res['percentage'])


def setup(cardinal, config):
    return TickerPlugin(cardinal, config)
