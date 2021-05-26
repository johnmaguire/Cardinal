import copy
import datetime
import random
from contextlib import contextmanager

import pytest
import pytest_twisted
import pytz
from mock import MagicMock, Mock, PropertyMock, call, patch
from twisted.internet import defer
from twisted.internet.task import Clock

from cardinal import util
from cardinal.bot import CardinalBot, user_info
from cardinal.unittest_util import get_mock_db
from plugins.ticker import plugin
from plugins.ticker.plugin import (
    TickerPlugin,
    colorize,
    get_delta,
)


def make_iex_response(symbol, price=None, previous_close=None):
    # NOTE - Not all values here will make sense. We are just mocking out the
    # values that will be used.

    price = price or \
        random.randrange(95, 105) + random.random()
    previous_close = previous_close or \
        random.randrange(95, 105) + random.random()

    return {
        "symbol": symbol,
        "companyName": "Gamestop Corporation - Class A",
        "primaryExchange": "NEW YORK STOCK EXCHANGE, INC.",
        "calculationPrice": "iexlasttrade",
        "open": None,
        "openTime": None,
        "openSource": "official",
        "close": None,
        "closeTime": None,
        "closeSource": "official",
        "high": None,
        "highTime": 1611781163724,
        "highSource": "15 minute delayed price",
        "low": None,
        "lowTime": 1611760730732,
        "lowSource": "15 minute delayed price",
        "latestPrice": price,
        "latestSource": "IEX Last Trade",
        "latestTime": "January 27, 2021",
        "latestUpdate": 1611781197811,
        "latestVolume": None,
        "iexRealtimePrice": 368.495,
        "iexRealtimeSize": 16,
        "iexLastUpdated": 1611781357372,
        "delayedPrice": None,
        "delayedPriceTime": None,
        "oddLotDelayedPrice": None,
        "oddLotDelayedPriceTime": None,
        "extendedPrice": None,
        "extendedChange": None,
        "extendedChangePercent": None,
        "extendedPriceTime": None,
        "previousClose": previous_close,
        "previousVolume": 178587974,
        "change": 199.52,
        "changePercent": (price - previous_close) / previous_close,
        "volume": None,
        "iexMarketPercent": 0.017150159906855904,
        "iexVolume": 1570454,
        "avgTotalVolume": 56932477,
        "iexBidPrice": 0,
        "iexBidSize": 0,
        "iexAskPrice": 0,
        "iexAskSize": 0,
        "iexOpen": 368.495,
        "iexOpenTime": 1611781357372,
        "iexClose": 347.5,
        "iexCloseTime": 1611781197811,
        "marketCap": 24237068600,
        "peRatio": -82.15,
        "week52High": 380,
        "week52Low": 2.8,
        "ytdChange": 8.20285475583864,
        "lastTradeTime": 1611781197811,
        "isUSMarketOpen": False
    }

def get_fake_now(market_is_open=True):
    tz = pytz.timezone('America/New_York')
    fake_now = datetime.datetime.now(tz)
    if market_is_open:
        # Ensure it is open
        fake_now = fake_now.replace(hour=10)
        while fake_now.weekday() >= 5:
            fake_now = fake_now - datetime.timedelta(days=1)
    else:
        # Ensure it is closed
        fake_now = fake_now.replace(hour=18)

    return fake_now


@contextmanager
def mock_api(response,
             fake_now=None):
    fake_now = fake_now or get_fake_now()
    responses = copy.deepcopy(response) \
        if isinstance(response, list) else \
        [copy.deepcopy(response)]

    response_mock = MagicMock()
    type(response_mock).status_code = PropertyMock(return_value=200)

    def mock_deferToThread(*args, **kwargs):
        response_mock.json.return_value = responses.pop(0)

        return response_mock

    with patch.object(plugin, 'deferToThread') as mock_defer, \
            patch.object(plugin, 'est_now', return_value=fake_now):
        mock_defer.side_effect = mock_deferToThread

        yield mock_defer


def test_get_delta():
    assert get_delta(105, 100) == 5.0
    assert get_delta(95, 100) == -5.0
    assert get_delta(100, 100) == 0


def test_colorize():
    assert colorize(-0.151) == '\x0304-0.15%\x03'
    assert colorize(-0.1) == '\x0304-0.10%\x03'
    assert colorize(0) == '\x03040.00%\x03'
    assert colorize(0.1) == '\x03090.10%\x03'
    assert colorize(0.159) == '\x03090.16%\x03'


class TestTickerPlugin:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self, request, tmpdir):
        self.api_key = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        self.channel = '#test'
        self.channels = [self.channel]
        self.stocks = [
            ['SPY', 'S&P 500'],
            ['DIA', 'Dow'],
            ['VEU', 'Foreign'],
            ['AGG', 'US Bond'],
        ]
        self.relay_bots = [
            {"nick": "relay.bot", "user": "relay", "vhost": "relay"},
        ]

        d = tmpdir.mkdir('storage')

        get_db, self.db = get_mock_db()
        self.mock_cardinal = Mock(spec=CardinalBot)
        self.mock_cardinal.network = self.network = 'irc.darkscience.net'
        self.mock_cardinal.storage_path = str(d.dirpath())
        self.mock_cardinal.get_db.side_effect = get_db

        self.plugin = TickerPlugin(self.mock_cardinal, {
            'api_key': self.api_key,
            'channels': self.channels,
            'stocks': self.stocks,
            'relay_bots': self.relay_bots,
        })

    def test_config_defaults(self):
        plugin = TickerPlugin(self.mock_cardinal, {
            'api_key': self.api_key,
        })
        assert plugin.config['api_key'] == self.api_key
        assert plugin.config['channels'] == []
        assert plugin.config['stocks'] == []
        assert plugin.config['relay_bots'] == []

    def test_missing_api_key(self):
        with pytest.raises(KeyError):
            TickerPlugin(self.mock_cardinal, {})

    def test_missing_stocks(self):
        with pytest.raises(ValueError):
            TickerPlugin(self.mock_cardinal, {
                'api_key': self.api_key,
                'stocks': [
                    ['a', 'a'],
                    ['b', 'b'],
                    ['c', 'c'],
                    ['d', 'd'],
                    ['e', 'e'],
                    ['f', 'f'],
                ],
            })

    @defer.inlineCallbacks
    def test_send_ticker(self):
        responses = [
            make_iex_response('DIA',
                              previous_close=100,
                              price=200),
            make_iex_response('AGG',
                              previous_close=100,
                              price=150.50),
            make_iex_response('VEU',
                              previous_close=100,
                              price=105),
            make_iex_response('SPY',
                              previous_close=100,
                              price=50),
        ]

        with mock_api(responses, fake_now=get_fake_now(market_is_open=True)):
            yield self.plugin.send_ticker()

        # These should be ordered per the config
        self.mock_cardinal.sendMsg.assert_called_once_with(
            self.channel,
            'S&P 500 (\x02SPY\x02): \x0304-50.00%\x03 | '
            'Dow (\x02DIA\x02): \x0309100.00%\x03 | '
            'Foreign (\x02VEU\x02): \x03095.00%\x03 | '
            'US Bond (\x02AGG\x02): \x030950.50%\x03'
        )

    @pytest.mark.parametrize("dt,should_send_ticker,should_do_predictions", [
        (datetime.datetime(2020, 3, 21, 16, 0, 0),  # Saturday 4pm
         False,
         False,),
        (datetime.datetime(2020, 3, 22, 16, 0, 0),  # Sunday 4pm
         False,
         False,),
        (datetime.datetime(2020, 3, 23, 15, 45, 45),  # Monday 3:45pm
         True,
         False,),
        (datetime.datetime(2020, 3, 23, 16, 0, 30),  # Monday 4pm
         True,
         True,),
        (datetime.datetime(2020, 3, 23, 16, 15, 0),  # Monday 4:15pm
         False,
         False,),
        (datetime.datetime(2020, 3, 27, 9, 15, 0),  # Friday 9:15am
         False,
         False,),
        (datetime.datetime(2020, 3, 27, 9, 30, 15),  # Friday 9:30am
         True,
         True,),
        (datetime.datetime(2020, 3, 27, 9, 45, 15),  # Friday 9:45am
         True,
         False,),
    ])
    @patch.object(plugin.TickerPlugin, 'do_predictions')
    @patch.object(plugin.TickerPlugin, 'send_ticker')
    @patch.object(util, 'sleep')
    @patch.object(plugin, 'est_now')
    @pytest_twisted.inlineCallbacks
    def test_tick(self,
                  est_now,
                  sleep,
                  send_ticker,
                  do_predictions,
                  dt,
                  should_send_ticker,
                  should_do_predictions):
        est_now.return_value = dt

        yield self.plugin.tick()

        if should_send_ticker:
            send_ticker.assert_called_once_with()
        else:
            assert send_ticker.mock_calls == []

        if should_do_predictions:
            sleep.assert_called_once_with(60)
            do_predictions.assert_called_once_with()
        else:
            assert sleep.mock_calls == []
            assert do_predictions.mock_calls == []

    @pytest.mark.parametrize("market_is_open", [True, False])
    @patch.object(util, 'reactor', new_callable=Clock)
    @pytest_twisted.inlineCallbacks
    def test_do_predictions(self, mock_reactor, market_is_open):
        symbol = 'SPY'
        base = 100.0

        user1 = 'user1'
        user2 = 'user2'
        prediction1 = 105.0
        prediction2 = 96.0

        actual = 95.0

        yield self.plugin.save_prediction(
            symbol,
            user1,
            base,
            prediction1,
        )
        yield self.plugin.save_prediction(
            symbol,
            user2,
            base,
            prediction2,
        )

        assert len(self.db['predictions']) == 1
        assert len(self.db['predictions'][symbol]) == 2

        response = make_iex_response(symbol, price=actual)

        with mock_api(response, fake_now=get_fake_now(market_is_open)):
            d = self.plugin.do_predictions()
            mock_reactor.advance(15)

            yield d

        assert len(self.mock_cardinal.sendMsg.mock_calls) == 3
        self.mock_cardinal.sendMsg.assert_called_with(
            self.channel,
            '{} had the closest guess for \x02{}\x02 out of {} predictions '
            'with a prediction of {:.2f} (\x0304{:.2f}%\x03) '
            'compared to the actual {} of {:.2f} (\x0304{:.2f}%\x03).'.format(
                user2,
                symbol,
                2,
                prediction2,
                -4,
                'open' if market_is_open else 'close',
                actual,
                -5))

    @patch.object(plugin, 'est_now')
    def test_send_prediction(self, mock_now):
        prediction = 105
        actual = 110
        base = 100
        nick = "nick"
        symbol = "SPY"

        # Set the datetime to a known value so the message can be tested
        tz = pytz.timezone('America/New_York')
        mock_now.return_value = tz.localize(
            datetime.datetime(2020, 3, 20, 10, 50, 0, 0))

        prediction_ = {'when': '2020-03-20 10:50:00 EDT',
                       'prediction': prediction,
                       'base': base,
                       }
        self.plugin.send_prediction(nick, symbol, prediction_, actual)

        message = ("Prediction by nick for \x02SPY\02: 105.00 (\x03095.00%\x03). "
                   "Actual value at open: 110.00 (\x030910.00%\x03). "
                   "Prediction set at 2020-03-20 10:50:00 EDT.")
        self.mock_cardinal.sendMsg.assert_called_once_with('#test', message)

    @pytest.mark.parametrize("symbol,input_msg,output_msg,market_is_open", [
        ("SPY",
         ".predict SPY +5%",
         "Prediction by nick for \x02SPY\x02 at market close: 105.00 (\x03095.00%\x03) ",
         True,
         ),
        ("SPY",
         ".predict SPY -5%",
         "Prediction by nick for \x02SPY\x02 at market close: 95.00 (\x0304-5.00%\x03) ",
         True,
         ),
        ("SPY",
         ".predict SPY -5%",
         "Prediction by nick for \x02SPY\x02 at market open: 95.00 (\x0304-5.00%\x03) ",
         False,
         ),
        # testing a few more formats of stock symbols
        ("^RUT",
         ".predict ^RUT -5%",
         "Prediction by nick for \x02^RUT\x02 at market open: 95.00 (\x0304-5.00%\x03) ",
         False,
         ),
        ("REE.MC",
         ".predict REE.MC -5%",
         "Prediction by nick for \x02REE.MC\x02 at market open: 95.00 (\x0304-5.00%\x03) ",
         False,
         ),
        ("LON:HDLV",
         ".predict LON:HDLV -5%",
         "Prediction by nick for \x02LON:HDLV\x02 at market open: 95.00 (\x0304-5.00%\x03) ",
         False,
         ),
    ])
    @pytest_twisted.inlineCallbacks
    def test_predict(self,
                     symbol,
                     input_msg,
                     output_msg,
                     market_is_open):
        channel = "#finance"

        fake_now = get_fake_now(market_is_open=market_is_open)

        kwargs = {'previous_close': 100} if market_is_open else {'price': 100}
        response = make_iex_response(symbol, **kwargs)

        with mock_api(response, fake_now=fake_now):
            yield self.plugin.predict(self.mock_cardinal,
                                      user_info("nick", "user", "vhost"),
                                      channel,
                                      input_msg)

        assert symbol in self.db['predictions']
        assert len(self.db['predictions'][symbol]) == 1

        self.mock_cardinal.sendMsg.assert_called_once_with(
            channel,
            output_msg)

    @pytest.mark.parametrize("message_pairs", [
        ((".predict SPY +5%",
          "Prediction by nick for \x02SPY\x02 at market close: 105.00 (\x03095.00%\x03) ",
          ),
         (".predict SPY -5%",
          "Prediction by nick for \x02SPY\x02 at market close: 95.00 (\x0304-5.00%\x03) "
          "(replaces old prediction of 105.00 (\x03095.00%\x03) set at {})"
          ),
         )
    ])
    @pytest_twisted.inlineCallbacks
    def test_predict_replace(self, message_pairs):
        channel = "#finance"
        symbol = 'SPY'

        response = make_iex_response(symbol, previous_close=100)

        fake_now = get_fake_now()
        for input_msg, output_msg in message_pairs:
            with mock_api(response, fake_now):
                yield self.plugin.predict(self.mock_cardinal,
                                          user_info("nick", "user", "vhost"),
                                          channel,
                                          input_msg)

                assert symbol in self.db['predictions']
                assert len(self.db['predictions'][symbol]) == 1

                self.mock_cardinal.sendMsg.assert_called_with(
                    channel,
                    output_msg.format(fake_now.strftime('%Y-%m-%d %H:%M:%S %Z'))
                    if '{}' in output_msg else
                    output_msg)

    @pytest.mark.parametrize("input_msg,output_msg", [
        ("<nick> .predict SPY +5%",
         "Prediction by nick for \x02SPY\x02 at market close: 105.00 (\x03095.00%\x03) ",
         ),
        ("<nick> .predict SPY -5%",
         "Prediction by nick for \x02SPY\x02 at market close: 95.00 (\x0304-5.00%\x03) ",
         ),
    ])
    @pytest_twisted.inlineCallbacks
    def test_predict_relayed_relay_bot(self, input_msg, output_msg):
        symbol = 'SPY'
        channel = "#finance"

        response = make_iex_response(symbol, previous_close=100)
        with mock_api(response):
            yield self.plugin.predict_relayed(
                self.mock_cardinal,
                user_info("relay.bot", "relay", "relay"),
                channel,
                input_msg)

        assert symbol in self.db['predictions']
        assert len(self.db['predictions'][symbol]) == 1

        self.mock_cardinal.sendMsg.assert_called_once_with(
            channel,
            output_msg)

    @pytest.mark.parametrize("input_msg", [
        "<whoami> .predict SPY +5%",
        "<whoami> .predict SPY -5%",
    ])
    @pytest_twisted.inlineCallbacks
    def test_predict_relayed_not_relay_bot(self, input_msg):
        channel = "#finance"

        yield self.plugin.predict_relayed(
            self.mock_cardinal,
            user_info("nick", "user", "vhost"),
            channel,
            input_msg)

        assert len(self.db['predictions']) == 0
        assert self.mock_cardinal.sendMsg.mock_calls == []

    @pytest.mark.parametrize("user,message,value,expected", [
        (
            "whoami",
            ".predict SPY 5%",
            100,
            ("whoami", "SPY", 105, 100),
        ),
        (
            "whoami",
            ".predict SPY +5%",
            100,
            ("whoami", "SPY", 105, 100),
        ),
        (
            "whoami",
            ".predict SPY -5%",
            100,
            ("whoami", "SPY", 95, 100),
        ),
    ])
    @pytest_twisted.inlineCallbacks
    def test_parse_prediction_open(
            self,
            user,
            message,
            value,
            expected,
    ):
        symbol = 'SPY'

        response = make_iex_response(symbol, previous_close=value)
        with mock_api(response):
            result = yield self.plugin.parse_prediction(user, message)

        assert result == expected

    @pytest.mark.parametrize("user,message,value,expected", [
        (
            "whoami",
            ".predict SPY 500",
            100,
            ("whoami", "SPY", 500, 100),
        ),
        (
            "whoami",
            ".predict SPY $100",
            100,
            ("whoami", "SPY", 100, 100),
        ),
    ])
    @pytest_twisted.inlineCallbacks
    def test_parse_prediction_open_dollar_amount(
            self,
            user,
            message,
            value,
            expected,
    ):
        symbol = 'SPY'

        response = make_iex_response(symbol, previous_close=value)
        with mock_api(response):
            result = yield self.plugin.parse_prediction(user, message)

        assert result == expected

    @pytest.mark.parametrize("user,message,value,expected", [
        (
            "whoami",
            ".predict SPY 5%",
            100,
            ("whoami", "SPY", 105, 100),
        ),
        (
            "whoami",
            ".predict SPY +5%",
            100,
            ("whoami", "SPY", 105, 100),
        ),
        (
            "whoami",
            ".predict SPY -5%",
            100,
            ("whoami", "SPY", 95, 100),
        ),
    ])
    @pytest_twisted.inlineCallbacks
    def test_parse_prediction_close(
            self,
            user,
            message,
            value,
            expected,
    ):
        symbol = 'SPY'

        response = make_iex_response(symbol, price=value)
        with mock_api(response, fake_now=get_fake_now(market_is_open=False)):
            result = yield self.plugin.parse_prediction(user, message)

        assert result == expected

    @patch.object(plugin, 'est_now')
    def test_save_prediction(self, mock_now):
        symbol = 'SPY'
        nick = 'whoami'
        base = 100
        prediction = 105

        tz = pytz.timezone('America/New_York')
        mock_now.return_value = tz.localize(datetime.datetime(
            2020,
            3,
            23,
            12,
            0,
            0,
        ))
        self.plugin.save_prediction(
            symbol,
            nick,
            base,
            prediction,
        )

        assert symbol in self.db['predictions']
        assert nick in self.db['predictions'][symbol]
        actual = self.db['predictions'][symbol][nick]
        assert actual == {
            'when': '2020-03-23 12:00:00 EDT',
            'base': base,
            'prediction': prediction,
        }

    @defer.inlineCallbacks
    def test_get_daily(self):
        symbol = 'SPY'
        price = 101.0
        previous_close = 102.0

        response = make_iex_response(symbol,
                                     price=price,
                                     previous_close=previous_close,
                                     )

        expected = {
            'symbol': symbol,
            'price': price,
            'previous close': previous_close,
            # this one is calculated by our mock response function so it
            # doesn't really test anything anymore
            'change': ((price - previous_close) / previous_close) * 100,
        }

        with mock_api(response):
            result = yield self.plugin.get_daily(symbol)
        assert result == expected

    @patch.object(plugin, 'est_now')
    def test_market_is_open(self, mock_now):
        tz = pytz.timezone('America/New_York')

        # Nothing special about this time - it's a Thursday 7:49pm
        mock_now.return_value = tz.localize(datetime.datetime(
            2020,
            3,
            19,
            19,
            49,
            55,
            0,
        ))
        assert plugin.market_is_open() is False

        # The market was open earlier though
        mock_now.return_value = tz.localize(datetime.datetime(
            2020,
            3,
            19,
            13,
            49,
            55,
            0,
        ))
        assert plugin.market_is_open() is True

        # But not before 9:30am
        mock_now.return_value = tz.localize(datetime.datetime(
            2020,
            3,
            19,
            9,
            29,
            59,
            0,
        ))
        assert plugin.market_is_open() is False

        # Or this weekend
        mock_now.return_value = tz.localize(datetime.datetime(
            2020,
            3,
            14,
            13,
            49,
            55,
            0,
        ))
        assert plugin.market_is_open() is False
