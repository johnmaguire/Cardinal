from collections import OrderedDict
from datetime import date, datetime
from dateutil.easter import easter
from dateutil.relativedelta import relativedelta as rd, MO, TH, FR
import logging
import re

from holidays.constants import (
    JAN,
    FEB,
    MAY,
    JUL,
    SEP,
    NOV,
    DEC,
)
from holidays.constants import FRI, SAT, SUN
from holidays.holiday_base import HolidayBase
from twisted.internet import defer, error, reactor
from twisted.internet.threads import deferToThread
import pytz
import requests

from cardinal import util
from cardinal.bot import user_info
from cardinal.decorators import command, help, regex
from cardinal.util import F


# NYSE currently has nine (9) trading holidays: New Year's Day, MLK Jr. Day,
# Washington's Birthday, Good Friday, Memorial Day, Independence Day, Labor
# Day, Thanksgiving Day, and Christmas Day. This does not take into account
# early closes.
#
# Reference:
# https://github.com/dr-prodigy/python-holidays/blob/master/holidays/countries/united_states.py
class NYSEHolidays(HolidayBase):
    def __init__(self, **kwargs):
        self.observed = True
        HolidayBase.__init__(self, **kwargs)

    def _populate(self, year):
        # New Year's Day
        name = "New Year's Day"
        self[date(year, JAN, 1)] = name
        if self.observed and date(year, JAN, 1).weekday() == SUN:
            self[date(year, JAN, 1) + rd(days=+1)] = name + " (Observed)"
        elif self.observed and date(year, JAN, 1).weekday() == SAT:
            # Add December 31st from the previous year without triggering
            # the entire year to be added
            expand = self.expand
            self.expand = False
            self[date(year, JAN, 1) + rd(days=-1)] = name + " (Observed)"
            self.expand = expand
        # The next year's observed New Year's Day can be in this year
        # when it falls on a Friday (i.e. Jan 1st is a Saturday)
        if self.observed and date(year, DEC, 31).weekday() == FRI:
            self[date(year, DEC, 31)] = name + " (Observed)"

        # Martin Luther King Jr. Day
        name = "Martin Luther King Jr. Day"
        self[date(year, JAN, 1) + rd(weekday=MO(+3))] = name

        # Washington's Birthday
        name = "Washington's Birthday"
        self[date(year, FEB, 1) + rd(weekday=MO(+3))] = name

        # Good Friday
        name = "Good Friday"
        self[easter(year) + rd(weekday=FR(-1))] = name

        # Memorial Day
        name = "Memorial Day"
        self[date(year, MAY, 31) + rd(weekday=MO(-1))] = name

        # Independence Day
        name = "Independence Day"
        self[date(year, JUL, 4)] = name
        if self.observed and date(year, JUL, 4).weekday() == SAT:
            self[date(year, JUL, 4) + rd(days=-1)] = name + " (Observed)"
        elif self.observed and date(year, JUL, 4).weekday() == SUN:
            self[date(year, JUL, 4) + rd(days=+1)] = name + " (Observed)"

        # Labor Day
        name = "Labor Day"
        self[date(year, SEP, 1) + rd(weekday=MO)] = name

        # Thanksgiving Day
        name = "Thanksgiving Day"
        self[date(year, NOV, 1) + rd(weekday=TH(+4))] = name

        # Christmas Day
        name = "Christmas Day"
        self[date(year, DEC, 25)] = name
        if self.observed and date(year, DEC, 25).weekday() == SAT:
            self[date(year, DEC, 25) + rd(days=-1)] = name + " (Observed)"
        elif self.observed and date(year, DEC, 25).weekday() == SUN:
            self[date(year, DEC, 25) + rd(days=+1)] = name + " (Observed)"


# Class populated with NYSE holidays
HOLIDAYS = NYSEHolidays()

# IEX API Endpoint
IEX_QUOTE_API_URL = "https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={token}"  # noqa: E501

# TwelveData API Endpoint
TD_QUOTE_API_URL = "https://api.twelvedata.com/quote?symbol={symbol}&apikey={token}"  # noqa: E501

# Regex pattern that matches PyLink relay bots
RELAY_REGEX = r'^(?:<(.+?)>\s+)'

# For 'stock' command - checking stock price
STOCK_RELAY_REGEX = RELAY_REGEX + r'(\.stock.*?)$'

# For 'predict' command - predicting stock price
PREDICT_REGEX = r'^(.+?) (?:([-+])?(\d+(?:\.\d+)?)%|\$?(\d+(?:\.\d+)?))$'  # noqa: E501

# For 'predict' command - predicting a stock price
PREDICT_RELAY_REGEX = RELAY_REGEX + r'(\.predict.*?)$'


def est_now():
    tz = pytz.timezone('America/New_York')
    now = datetime.now(tz)

    return now


def market_is_open():
    now = est_now()

    # Determine if the market is currently open
    is_market_closed = (now in HOLIDAYS) or \
        (now.weekday() >= 5) or \
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


class TickerPlugin:
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
        if len(self.config["stocks"]) > 6:
            raise ValueError("No more than 6 stocks may be present in ticker "
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

    @property
    def stocks(self):
        return OrderedDict(self.config["stocks"])

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

        self.call_id = reactor.callLater(seconds_to_sleep, self.tick)

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
            (now in HOLIDAYS) or
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
        for symbol, name in self.stocks.items():
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
        results = {}
        for success, result in dl_results:
            if not success:
                continue

            symbol, change = result
            results.update({symbol: change})

        if results:
            message = self.format_ticker(results)
            for channel in self.config["channels"]:
                self.cardinal.sendMsg(channel, message)

    def format_ticker(self, results):
        message_parts = []
        for symbol, name in self.stocks.items():
            if symbol in results:
                message_parts.append(
                    self.format_symbol(symbol, results[symbol])
                )

        message = " | ".join(message_parts)
        return message

    def format_symbol(self, symbol, change):
        name = self.stocks[symbol]

        return "{name} ({symbol}): {change}".format(
                symbol=F.bold(symbol),
                name=name,
                change=colorize(change),
            )

    @defer.inlineCallbacks
    def do_predictions(self):
        # Loop each prediction, grouped by symbols to avoid rate limits
        with self.db() as db:
            # TODO will this generator still work if it's iterated outside the
            # context manager?
            predicted_symbols = list(db['predictions'].keys())

        for symbol in predicted_symbols:
            try:
                data = yield self.get_daily(symbol)

                # this is not 100% accurate as to the value at open... it's
                # just a value close to the open, iex cloud doesn't let us get
                # at the true open without paying
                actual = data['price']
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
                    "{} had the closest guess for {} out of {} "
                    "predictions with a prediction of {:.2f} ({}) "
                    "compared to the actual {} of {:.2f} ({}).".format(
                        closest_nick,
                        F.bold(symbol),
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
                "Prediction by {} for \x02{}\x02: {:.2f} ({}). "
                "Actual value at {}: {:.2f} ({}). "
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

    @command('stock')
    @help("Check the latest price of a stock")
    @help("Syntax: .stock <stock symbol>")
    @defer.inlineCallbacks
    def stock(self, cardinal, user, channel, msg):
        nick = user.nick  # other values may not exist for relayed users

        parts = msg.split(' ')
        if len(parts) != 2:
            cardinal.sendMsg(channel, "Syntax: .stock <stock symbol>")
            return

        symbol = parts[1].upper()
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
            "{} (\x02{}\x02) = {:.2f} USD - Daily Change: {} - https://finance.yahoo.com/quote/{}".format(
                data['companyName'],
                data['symbol'],
                data['price'],
                colorize(data['change']),
                data['symbol']))

    @regex(STOCK_RELAY_REGEX)
    @defer.inlineCallbacks
    def stock_relayed(self, cardinal, user, channel, msg):
        """Hack to support relayed messages"""
        match = re.match(STOCK_RELAY_REGEX, msg)

        # this regex should only match when a relay bot is relaying a message
        # for another user - make sure this is really a relay bot
        if not self.is_relay_bot(user):
            return

        user = user_info(util.strip_formatting(match.group(1)),
                         user.user,
                         user.vhost,
                         )

        yield self.stock(cardinal, user, channel, match.group(2))

    @command('predict')
    @help("Predict a stock price at the next market open/close")
    @help("Syntax: .predict <stock> [-]<X>%  |  .predict <stock> $<X>")
    @defer.inlineCallbacks
    def predict(self, cardinal, user, channel, msg):
        nick = user.nick

        try:
            msg = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel,
                             "Syntax: .predict <stock> [-]<X>%  |"
                             "  .predict <stock> $<X>")
            return

        if not re.match(PREDICT_REGEX, msg):
            cardinal.sendMsg(channel,
                             "Syntax: .predict <stock> [-]<X>%  |"
                             "  .predict <stock> $<X>")
            return

        try:
            prediction = yield self.parse_prediction(nick, msg)
        except Exception as exc:
            self.logger.warning("Error trying to parse prediction: {}"
                                .format(exc))
            cardinal.sendMsg(
                channel,
                "{}: Are you sure the symbol is correct?".format(user.nick))
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

    @regex(PREDICT_RELAY_REGEX)
    @defer.inlineCallbacks
    def predict_relayed(self, cardinal, user, channel, msg):
        """Hack to support relayed messages"""
        match = re.match(PREDICT_RELAY_REGEX, msg)

        # this regex should only match when a relay bot is relaying a message
        # for another user - make sure this is really a relay bot
        if not self.is_relay_bot(user):
            return

        user = user_info(util.strip_formatting(match.group(1)),
                         user.user,
                         user.vhost,
                         )

        yield self.predict(cardinal, user, channel, match.group(2))

    @defer.inlineCallbacks
    def parse_prediction(self, nick, message):
        match = re.match(PREDICT_REGEX, message)

        data = yield self.get_daily(match.group(1))
        if market_is_open():
            # get value at previous close
            base = data['previous close']
        else:
            # get latest price
            base = data['price']

        symbol = data['symbol']  # consistent casing

        negative_percentage = match.group(2) == '-'
        percentage = float(match.group(3)) if match.group(3) else None
        price = float(match.group(4)) if match.group(4) else None

        if percentage is not None:
            prediction = percentage * .01 * base
            if negative_percentage:
                prediction = base - prediction
            else:
                prediction = base + prediction
        elif price is not None:
            prediction = price
        else:
            # this shouldn't happen
            raise Exception("No price or percentage: {}".format(message))

        return (
            nick,
            symbol,
            prediction,
            base,
        )

    def save_prediction(self, symbol, nick, base, prediction):
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

    def get_daily(self, symbol):
        return self.make_td_request(symbol)

    @defer.inlineCallbacks
    def make_td_request(self, symbol):
        url = TD_QUOTE_API_URL.format(
            symbol=symbol,
            token=self.config["api_key"],
        )
        r = yield deferToThread(requests.get, url)
        data = r.json()

        try:
            price = float(data['close'])
            previous_close = float(data['previous_close'])
            change_percent = ((price - previous_close) / previous_close) * 100
            return ({'symbol': data['symbol'],
                     'companyName': data['name'],
                     'exchange': data['exchange'],
                     'price': price,
                     'previous close': previous_close,
                     'change': change_percent,
                     })
        except KeyError as e:
            self.logger.error("{}, with data: {}".format(e, data))
            raise

    @defer.inlineCallbacks
    def make_iex_request(self, symbol):
        url = IEX_QUOTE_API_URL.format(
            symbol=symbol,
            token=self.config["api_key"],
        )
        r = yield deferToThread(requests.get, url)
        data = r.json()

        try:
            price = float(data['latestPrice'])
            previous_close = float(data['previousClose'])
            change_percent = ((price - previous_close) / previous_close) * 100
            return ({'symbol': data['symbol'],
                     'companyName': data['companyName'],
                     'exchange': data['primaryExchange'],
                     'price': price,
                     'previous close': previous_close,
                     'change': change_percent,
                     })
        except KeyError as e:
            self.logger.error("{}, with data: {}".format(e, data))
            raise


entrypoint = TickerPlugin
