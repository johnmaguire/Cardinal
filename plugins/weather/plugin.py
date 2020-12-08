from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
from past.utils import old_div
import hashlib
import hmac
import logging
import time
import urllib.request, urllib.parse, urllib.error
import uuid
from base64 import b64encode

import requests

from cardinal.decorators import command, help

FORECAST_URL = "https://weather-ydn-yql.media.yahoo.com/forecastrss"
SIGNATURE_CONCAT = '&'

# Hopefully these don't get banned by Yahoo -- if they do, I'll have to make
# them config options.
APP_ID = "jpfkwT7i"
CONSUMER_KEY = "dj0yJmk9YVpma1VWcno1U01wJmQ9WVdrOWFuQm1hM2RVTjJrbWNHbzlNQS0t" \
    "JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTRk"
CONSUMER_SECRET = "b816de899743153300c2c123521bb247cfb0c92a"


class WeatherPlugin(object):
    def __init__(self, cardinal):
        self.logger = logging.getLogger(__name__)
        self.db = cardinal.get_db('weather')

    def api_call(self, method, url, params):
        method = method.upper()

        oauth_params = {
            'oauth_consumer_key': CONSUMER_KEY,
            'oauth_nonce': uuid.uuid4().hex,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_version': '1.0',
        }

        merged_params = params.copy()
        merged_params.update(oauth_params)

        # Sort and canonicalize the params
        sorted_params = [k + '=' + urllib.parse.quote(merged_params[k], safe='')
                         for k in sorted(merged_params.keys())]

        signature_string = method + SIGNATURE_CONCAT + \
            urllib.parse.quote(url, safe='') + SIGNATURE_CONCAT + \
            urllib.parse.quote(SIGNATURE_CONCAT.join(sorted_params), safe='')

        # Generate signature
        composite_key = \
            urllib.parse.quote(CONSUMER_SECRET, safe='') + SIGNATURE_CONCAT
        oauth_signature = b64encode(hmac.new(composite_key.encode('utf-8'),
                                             signature_string.encode('utf-8'),
                                             hashlib.sha1).digest())

        oauth_params['oauth_signature'] = oauth_signature.decode('utf-8')
        auth_header = 'OAuth ' + ', '.join(
            ['{}="{}"'.format(k, v) for k, v in oauth_params.items()])

        res = requests.get(url, params=params, headers={
            'Authorization': auth_header,
            'X-Yahoo-App-Id': APP_ID,
        })
        res.raise_for_status()

        return res

    def get_forecast(self, location):
        params = {
            'location': location,
            'format': 'json',
        }

        return self.api_call('GET', FORECAST_URL, params)

    @command('setw')
    @help("Set your default weather location.")
    @help("Syntax: .setw <location>")
    def set_weather(self, cardinal, user, channel, msg):
        try:
            location = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .setw <location>")
            return

        try:
            res = self.get_forecast(location).json()
            location = "{}, {}, {}".format(res['location']['city'].strip(),
                                           res['location']['region'].strip(),
                                           res['location']['country'].strip())
        except Exception:
            cardinal.sendMsg(channel, "Sorry, I can't find that location.")
            self.logger.exception(
                "Error test fetching for location: '{}'".format(location))
            return

        with self.db() as db:
            db[user.nick] = location

        cardinal.sendMsg(channel, '{}: Your default weather location is now '
                                  'set to {}. Next time you want the weather '
                                  'at this location, just use .weather or .w!'
                                  .format(user.nick, location))

    @command(['weather', 'w'])
    @help("Retrieves the weather using the Yahoo! weather API.")
    @help("Syntax: .weather [location]")
    def weather(self, cardinal, user, channel, msg):
        try:
            location = msg.split(' ', 1)[1]
        except IndexError:
            with self.db() as db:
                try:
                    location = db[user.nick]
                except KeyError:
                    cardinal.sendMsg(channel, "Syntax: .weather <location>")
                    return

        try:
            res = self.get_forecast(location).json()
        except Exception:
            cardinal.sendMsg(channel, "Error fetching weather data.")
            self.logger.exception(
                "Error fetching forecast for location '{}'".format(location))
            return

        try:
            location = "{}, {}, {}".format(res['location']['city'].strip(),
                                           res['location']['region'].strip(),
                                           res['location']['country'].strip())
        except KeyError:
            cardinal.sendMsg(channel,
                             "Couldn't find weather data for your location.")
            return

        condition = res['current_observation']['condition']['text']
        temperature = \
            int(res['current_observation']['condition']['temperature'])
        temperature_c = old_div((temperature - 32) * 5,9)
        humidity = int(res['current_observation']['atmosphere']['humidity'])
        winds = float(res['current_observation']['wind']['speed'])
        winds_k = round(winds * 1.609344, 2)
        cardinal.sendMsg(
            channel,
            "[ {} | {} | Temp: {} F ({} C) | Humidity: {}% |"
            " Winds: {} mph ({} kph) ]".format(location,
                                               condition,
                                               temperature,
                                               temperature_c,
                                               humidity,
                                               winds,
                                               winds_k))


def setup(cardinal):
    return WeatherPlugin(cardinal)
