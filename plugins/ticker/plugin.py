from builtins import object
import datetime
import logging
import re

import pytz
import requests
from twisted.internet import defer, error, reactor
from twisted.internet.threads import deferToThread

from cardinal import util
from cardinal.bot import user_info
from cardinal.decorators import regex
from cardinal.util import F

# Alpha Vantage API key
AV_API_URL = "https://www.alphavantage.co/query"

# This is actually max tries, not max retries (for API requests)
MAX_RETRIES = 3
RETRY_WAIT = 15

# Supports relayed messages
CHECK_REGEX = r'^(?:<(.+?)>\s+)?!check (\^?[A-Za-z]+(?:[:\.][A-Za-z]+)?)$'

# Supports relayed messages
PREDICT_REGEX = r'^(?:<(.+?)>\s+)?!predict (\^?[A-Za-z]+(?:[:\.][A-Za-z]+)?) ([-+])?(\d+(?:\.\d+)?)%$'  # noqa: E501


class ThrottledException(Exception):
    """An exception we raise when we believe we are being API throttled."""
    pass


def est_now():
    tz = pytz.timezone('America/New_York')
    now = datetime.datetime.now(tz)

    return now


def market_is_open():
    """Not aware of holidays or anything like that..."""
    now = est_now()

    # Determine if the market is currently open
    is_market_closed = (now.weekday() >= 5) or \
        (now.hour < 9 or now.hour >= 17) or \
        (now.hour == 9 and now.minute < 30) or \
        (now.hour == 16 and now.minute > 0)

    return not is_market_closed


def get_delta(new_value, old_value):
    return float(new_value) / float(old_value) * 100 - 100


def colorize(percentage):
    message = '{:.2f}%'.format(percentage)
    if percentage > 0:
        return F.C.light_green(message)
    else:
        return F.C.light_red(message)


class TickerPlugin(object):
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)
        self.cardinal = cardinal

        self.config = config or {}
        self.config.setdefault('api_key', None)
        self.config.setdefault('channels', [])
        self.config.setdefault('stocks', {})
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

        self.db = cardinal.get_db('ticker', default={
            'predictions': {},
        })

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
        now = est_now()
        minutes_to_sleep = 15 - now.minute % 15
        seconds_to_sleep = minutes_to_sleep * 60
        seconds_to_sleep = seconds_to_sleep - now.second

        self.call_id = reactor.callLater(minutes_to_sleep * 60, self.tick)

    def close(self, cardinal):
        if self.call_id:
            try:
                self.call_id.cancel()
            except error.AlreadyCancelled as e:
                self.logger.debug(e)

    @defer.inlineCallbacks
    def tick(self):
        """Send a message with daily stock movements"""
        # Start the timer for the next tick -- do this first, as the rest of
        # this function may take time. While that's OK, and it shouldn't take
        # anywhere close to 15 minutes, reloading the plugin during that time
        # could result in close() cancelling the event, and then wait() getting
        # called from the old (reloaded) instance.
        self.wait()

        # If it's after 4pm ET or before 9:30am ET on a weekday, or if it's
        # a weekend (Saturday or Sunday), don't tick, just wait.
        now = est_now()

        # Determine if the market is currently open
        is_market_open = not (
            (now.weekday() >= 5) or
            (now.hour < 9 or now.hour >= 17) or
            (now.hour == 9 and now.minute < 30) or
            (now.hour == 16 and now.minute > 0))

        # Determine if this is the market opening or market closing
        is_open = now.hour == 9 and now.minute == 30
        is_close = now.hour == 16 and now.minute == 0

        # Determine if we should do predictions after sending ticker
        should_do_predictions = True \
            if is_market_open and (is_open or is_close) \
            else False

        # If there are no stocks to send in the ticker, or no channels to send
        # them to, don't tick, just wait.
        should_send_ticker = is_market_open and \
            self.config["channels"] and self.config["stocks"]

        if should_send_ticker:
            yield self.send_ticker()

        if should_do_predictions:
            # Try to avoid hitting rate limiting (5 calls per minute) by giving
            # a minute of buffer after the ticker.
            yield util.sleep(60)
            yield self.do_predictions()

    @defer.inlineCallbacks
    def send_ticker(self):
        # Used a DeferredList so that we can make requests for all the symbols
        # we care about simultaneously
        deferreds = []
        for symbol, name in list(self.config["stocks"].items()):
            d = self.get_daily(symbol)
            deferreds.append(d)

            # convert result to a (symbol, delta) mapping for the list
            def errback(f):
                self.logger.error("Failed to get stock {}: {}".format(
                    symbol, f))
                return f

            def callback(res):
                return (res['symbol'], res['change'])

            d.addErrback(errback)
            d.addCallback(callback)

        dl = defer.DeferredList(deferreds)

        # Loop the results, ignoring errored requests
        dl_results = yield dl
        message_parts = []
        for success, result in dl_results:
            if not success:
                continue

            symbol, change = result
            message_parts.append(self.format_symbol(symbol, change))

        message = ' | '.join(sorted(message_parts))
        for channel in self.config["channels"]:
            self.cardinal.sendMsg(channel, message)

    def format_symbol(self, symbol, change):
        return "{name} (\x02{symbol}\x02): {change}".format(
                symbol=symbol,
                name=self.config["stocks"][symbol],
                change=colorize(change),
            )

    @defer.inlineCallbacks
    def do_predictions(self):
        # Loop each prediction, grouped by symbols to avoid rate limits
        with self.db() as db:
            predicted_symbols = list(db['predictions'].keys())

        for symbol in predicted_symbols:
            try:
                data = yield self.get_daily(symbol)

                actual = data['close']
            except Exception:
                self.logger.exception(
                    "Failed to fetch information for symbol {} -- skipping"
                    .format(symbol))
                for channel in self.config["channels"]:
                    self.cardinal.sendMsg(
                        channel, "Error with predictions for symbol {}."
                                 .format(symbol))
                continue

            # Loop each nick's prediction, and look for the closest prediction
            # for the current symbol
            closest_prediction = None
            closest_delta = None
            closest_nick = None

            with self.db() as db:
                predictions = db['predictions'][symbol]
                del db['predictions'][symbol]

            for nick, prediction in list(predictions.items()):
                # Check if this is the closest guess for the symbol so far
                delta = abs(actual - prediction['prediction'])
                if not closest_delta or delta < closest_delta:
                    closest_prediction = prediction['prediction']
                    closest_delta = delta
                    closest_nick = nick

                self.send_prediction(
                    nick,
                    symbol,
                    prediction,
                    actual,
                )

            market_open_close = 'open' if market_is_open() else 'close'
            for channel in self.config["channels"]:
                self.cardinal.sendMsg(
                    channel,
                    "{} had the closest guess for \x02{}\x02 out of {} "
                    "predictions with a prediction of {} ({}) "
                    "compared to the actual {} of {} ({}).".format(
                        closest_nick,
                        symbol,
                        len(predictions),
                        closest_prediction,
                        colorize(get_delta(closest_prediction,
                                           prediction['base'])),
                        market_open_close,
                        actual,
                        colorize(get_delta(actual, prediction['base'])),
                    ))

            # Try to avoid hitting rate limiting (5 calls per minute) by
            # only checking predictions of 4 symbols per minute
            yield util.sleep(15)

    def send_prediction(
        self,
        nick,
        symbol,
        prediction,
        actual,
    ):
        market_open_close = 'open' if market_is_open() else 'close'

        for channel in self.config["channels"]:
            self.cardinal.sendMsg(
                channel,
                "Prediction by {} for \x02{}\x02: {} ({}). "
                "Actual value at {}: {} ({}). "
                "Prediction set at {}.".format(
                    nick,
                    symbol,
                    prediction['prediction'],
                    colorize(get_delta(
                        prediction['prediction'], prediction['base'])),
                    market_open_close,
                    actual,
                    colorize(get_delta(
                        actual, prediction['base'])),
                    prediction['when']
                ))

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

            nick = util.strip_formatting(match.group(1))

        symbol = match.group(2).upper()
        try:
            data = yield self.get_daily(symbol)
        except Exception as exc:
            self.logger.warning("Error trying to look up symbol {}: {}".format(
                symbol, exc))
            cardinal.sendMsg(
                channel, "{}: I couldn't look that symbol up".format(nick))
            return

        cardinal.sendMsg(
            channel,
            "Symbol: \x02{}\x02 | Current: {} | Daily Change: {}".format(
                symbol,
                data['close'],
                colorize(data['change'])))

    @regex(PREDICT_REGEX)
    @defer.inlineCallbacks
    def predict(self, cardinal, user, channel, msg):
        try:
            prediction = yield self.parse_prediction(user, msg)
        except Exception as exc:
            self.logger.warning("Error trying to parse prediction: {}"
                                .format(exc))
            cardinal.sendMsg(
                channel,
                "{}: I couldn't look that symbol up".format(user.nick))
            return
        else:
            # This may happen if we matched the relay bot regex but a relay bot
            # didn't send the message
            if prediction is None:
                return

        nick, symbol, prediction, base = prediction

        # If the user already had a prediction for the symbol, create a message
        # with the old prediction's info
        try:
            with self.db() as db:
                old_prediction = db['predictions'][symbol][nick]
        except KeyError:
            old_str = ''
        else:
            old_str = '(replaces old prediction of {:.2f} ({}) set at {})' \
                .format(
                    old_prediction['prediction'],
                    colorize(get_delta(old_prediction['prediction'],
                                       old_prediction['base'])),
                    old_prediction['when'],
                )

        # Save the prediction
        self.save_prediction(symbol, nick, base, prediction)
        cardinal.sendMsg(
            channel,
            "Prediction by {} for \x02{}\x02 at market {}: {:.2f} ({}) {}"
            .format(nick,
                    symbol,
                    'close' if market_is_open() else 'open',
                    prediction,
                    colorize(get_delta(prediction, base)),
                    old_str))

    @defer.inlineCallbacks
    def parse_prediction(self, user, message):
        match = re.match(PREDICT_REGEX, message)

        # Fix nick if relay bot sent the message
        nick = user.nick
        if match.group(1):
            if not self.is_relay_bot(user):
                defer.returnValue(None)

            nick = util.strip_formatting(match.group(1))

        # Convert symbol to uppercase
        symbol = match.group(2).upper()

        data = yield self.get_daily(symbol)
        if market_is_open():
            # get value at previous close
            base = data['previous close']
        else:
            # get value at close
            base = data['close']

        prediction = float(match.group(4))
        negative = match.group(3) == '-'

        prediction = prediction * .01 * base
        if negative:
            prediction = base - prediction
        else:
            prediction = base + prediction

        defer.returnValue((
            nick,
            symbol,
            prediction,
            base,
        ))

    def save_prediction(self, symbol, nick, base, prediction):
        # @TODO base may not be necessary after switching to quote
        with self.db() as db:
            predictions = db['predictions'].get(symbol, {})
            predictions[nick] = {
                'when': est_now().strftime('%Y-%m-%d %H:%M:%S %Z'),
                'base': base,
                'prediction': prediction,
            }
            db['predictions'][symbol] = predictions

    def get_prediction(self, symbol, nick):
        with self.db() as db:
            return db['predictions'][symbol][nick]

    @defer.inlineCallbacks
    def get_daily(self, symbol):
        data = yield self.get_quote(symbol)
        defer.returnValue({'symbol': data['symbol'],
                           'close': data['price'],
                           'previous close': data['previous close'],
                           'open': data['open'],
                           'change': data['change percent'],
                           })

    @defer.inlineCallbacks
    def get_quote(self, symbol):
        data = yield self.make_av_request('GLOBAL_QUOTE',
                                          {'symbol': symbol})

        try:
            data = data['Global Quote']
        except:
            raise KeyError("Response missing expected 'Global Quote' key: {}"
                           .format(data))

        data = {k[4:]: v for k, v in list(data.items())}

        defer.returnValue({
            'symbol': data['symbol'],
            'open': float(data['open']),
            'high': float(data['high']),
            'low': float(data['low']),
            'price': float(data['price']),
            'volume': int(data['volume']),
            'latest trading day': datetime.datetime.strptime(
                data['latest trading day'],
                '%Y-%m-%d',
            ),
            'previous close': float(data['previous close']),
            'change': float(data['change']),
            'change percent': float(data['change percent'][:-1]),
        })

    @defer.inlineCallbacks
    def get_time_series_daily(self, symbol, outputsize='compact'):
        data = yield self.make_av_request('TIME_SERIES_DAILY',
                                          {'symbol': symbol,
                                           'outputsize': outputsize,
                                           })
        try:
            data = data['Time Series (Daily)']
        except KeyError:
            raise KeyError("Response missing expected 'Time Series (Daily)' "
                           "key: {}".format(data))

        for date, values in list(data.items()):
            # Strip prefixes like "4. " from "4. close" and convert values from
            # the API to float instead of string
            values = {k[3:]: float(v) for k, v in list(values.items())}
            data[date] = values

        defer.returnValue(data)

    @defer.inlineCallbacks
    def make_av_request(self, function, params=None):
        if params is None:
            params = {}
        params['function'] = function
        params['apikey'] = self.config["api_key"]
        params['datatype'] = 'json'

        retries_remaining = MAX_RETRIES
        while retries_remaining > 0:
            retries_remaining -= 1
            try:
                r = yield deferToThread(requests.get,
                                        AV_API_URL,
                                        params=params)
                result = r.json()

                # Detect rate limiting
                if 'Note' in result and 'call frequency' in result['Note']:
                    raise ThrottledException(result['Note'])
            except Exception:
                self.logger.exception("Failed to make request to AV API - "
                                      "retries remaining: {}".format(
                                          retries_remaining))

                # Raise the exception if we're out of retries
                if retries_remaining == 0:
                    raise
            # If we succeeded, don't retry
            else:
                break

            # Otherwise, sleep 15 seconds to avoid rate limits before retrying
            yield util.sleep(RETRY_WAIT)
            continue

        defer.returnValue(result)


def setup(cardinal, config):
    return TickerPlugin(cardinal, config)
