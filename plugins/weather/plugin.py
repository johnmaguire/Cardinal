import logging

import requests
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from cardinal.decorators import command, help


class Forecast:
    def __init__(
        self,
        location,
        condition,
        temperature_f,
        humidity,
        winds_mph
    ):
        self.location = location
        self.condition = condition
        self.temperature_f = temperature_f
        self.temperature_c = (temperature_f - 32) * 5 // 9
        self.humidity = humidity
        self.winds_mph = winds_mph
        self.winds_k = round(winds_mph * 1.609344, 2)


class OpenWeatherClient:
    API_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self, api_key):
        self.api_key = api_key

    @defer.inlineCallbacks
    def get_forecast(self, location) -> Forecast:
        params = {
            'q': location,
            'appid': self.api_key,
            'units': 'imperial',
            'lang': 'en',
        }

        r = yield deferToThread(
            requests.get,
            self.API_ENDPOINT,
            params=params
        )

        return self.parse_forecast(r.json())

    def parse_forecast(self, res):
        location = "{}, {}".format(res['name'].strip(),
                                   res['sys']['country'].strip())
        condition = res['weather'][0]['main']
        temperature = int(res['main']['temp'])
        humidity = int(res['main']['humidity'])
        winds = float(res['wind']['speed'])

        return Forecast(location, condition, temperature, humidity, winds)


class WeatherAPIClient:
    API_ENDPOINT = "https://api.weatherapi.com/v1/current.json"

    def __init__(self, api_key):
        self.api_key = api_key

    @defer.inlineCallbacks
    def get_forecast(self, location) -> Forecast:
        params = {
            'q': location,
            'key': self.api_key,
        }

        r = yield deferToThread(
            requests.get,
            self.API_ENDPOINT,
            params=params
        )

        return self.parse_forecast(r.json())

    def parse_forecast(self, res):
        location = res['location']['name']
        if res['location']['region']:
            location += ", {}, {}".format(res['location']['region'],
                                          res['location']['country'])
        else:
            location += ", {}".format(res['location']['country'])

        return Forecast(
            location=location,
            condition=res['current']['condition']['text'],
            temperature_f=res['current']['temp_f'],
            humidity=res['current']['humidity'],
            winds_mph=res['current']['wind_mph'],
        )


class WeatherPlugin:
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)
        self.db = cardinal.get_db('weather')

        if config is None:
            config = {}

        self.provider = config.get('provider', 'weatherapi')
        self.api_key = config.get('api_key', None)

        if self.provider == 'openweather':
            self.client = OpenWeatherClient(self.api_key)
        elif self.provider == 'weatherapi':
            self.client = WeatherAPIClient(self.api_key)
        else:
            raise Exception(f"Unknown weather provider: {self.provider}")

    @command('setw')
    @help("Set your default weather location.")
    @help("Syntax: @setw <location>")
    @defer.inlineCallbacks
    def set_weather(self, cardinal, user, channel, msg):
        try:
            location = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .setw <location>")
            return

        try:
            res = yield self.client.get_forecast(location)
        except Exception:
            cardinal.sendMsg(channel, "Sorry, I can't find that location.")
            self.logger.exception(
                "Error test fetching for location: '{}'".format(location)
            )
            return

        with self.db() as db:
            db[user.nick] = location

        cardinal.sendMsg(channel, '{}: Your default weather location is now '
                                  'set to {}. Next time you want the weather '
                                  'at this location, just use .weather or .w!'
                         .format(user.nick, res.location))

    @command(['weather', 'w'])
    @help("Retrieves the weather using the OpenWeatherMap API.")
    @help("Syntax: @weather [location]")
    @defer.inlineCallbacks
    def weather(self, cardinal, user, channel, msg):
        if self.api_key is None:
            cardinal.sendMsg(
                channel,
                "Weather plugin is not configured correctly. "
                "Please set API key."
            )

        try:
            location = msg.split(' ', 1)[1]
        except IndexError:
            with self.db() as db:
                try:
                    location = db[user.nick]
                except KeyError:
                    cardinal.sendMsg(
                        channel,
                        "Syntax: .weather <location> "
                        "(.setw <location> to make it permanent)"
                    )
                    return

        try:
            res = yield self.client.get_forecast(location)
        except Exception:
            cardinal.sendMsg(channel, "Error fetching weather data.")
            self.logger.exception(
                "Error fetching forecast for location '{}'".format(location))
            return

        cardinal.sendMsg(
            channel,
            "[ {} | {} | Temp: {} °F ({} °C) | Humidity: {}% |"
            " Winds: {} mph ({} km/h) ]".format(
                res.location,
                res.condition,
                res.temperature_f,
                res.temperature_c,
                res.humidity,
                res.winds_mph,
                res.winds_k)
        )


entrypoint = WeatherPlugin
