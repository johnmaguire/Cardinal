import hashlib
import hmac
import logging
import time
import urllib
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
    def __init__(self):
        self.logger = logging.getLogger(__name__)

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
        sorted_params = [k + '=' + urllib.quote(merged_params[k], safe='')
                         for k in sorted(merged_params.keys())]

        signature_string = method + SIGNATURE_CONCAT + \
            urllib.quote(url, safe='') + SIGNATURE_CONCAT + \
            urllib.quote(SIGNATURE_CONCAT.join(sorted_params), safe='')

        # Generate signature
        composite_key = \
            urllib.quote(CONSUMER_SECRET, safe='') + SIGNATURE_CONCAT
        oauth_signature = b64encode(hmac.new(composite_key,
                                             signature_string,
                                             hashlib.sha1).digest())

        oauth_params['oauth_signature'] = oauth_signature
        auth_header = 'OAuth ' + ', '.join(
            ['{}="{}"'.format(k, v) for k, v in oauth_params.iteritems()])

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

    @command(['weather', 'w'])
    @help("Retrieves the weather using the Yahoo! weather API.")
    @help("Syntax: .weather <location>")
    def weather(self, cardinal, user, channel, msg):
        try:
            location = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .weather <location>")
            return

        try:
            res = self.get_forecast(location).json()
        except Exception:
            cardinal.sendMsg(channel, "Error fetching weather data.")
            self.logger.exception(
                "Error fetching forecast for location '{}'".format(location))

        try:
            location = "{}, {}, {}".format(res['location']['city'],
                                           res['location']['region'],
                                           res['location']['country'])
        except KeyError:
            cardinal.sendMsg(channel,
                             "Couldn't find weather data for your location.")
            return

        condition = res['current_observation']['condition']['text']
        temperature = \
            int(res['current_observation']['condition']['temperature'])
        temperature_c = (temperature - 32) * 5/9
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


def setup():
    return WeatherPlugin()
