import logging

import requests
from requests import Response

from cardinal.decorators import command, help

API_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"
# Hardcoded key for Cardinal
API_KEY = "7d00a4a07f7d55d9894aae06b0b473cb"


class WeatherPlugin:
    def __init__(self, cardinal):
        self.logger = logging.getLogger(__name__)
        self.db = cardinal.get_db('weather')

    def get_forecast(self, location) -> Response:
        params = {
            'q': location,
            'appid': API_KEY,
            'units': 'imperial',
            'lang': 'en',
        }

        return requests.get(API_ENDPOINT, params=params)

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
            location = "{}, {}".format(res['name'].strip(),
                                       res['sys']['country'].strip())
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
                         .format(user.nick, location))

    @command(['weather', 'w'])
    @help("Retrieves the weather using the OpenWeatherMap API.")
    @help("Syntax: .weather [location]")
    def weather(self, cardinal, user, channel, msg):
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
            res = self.get_forecast(location).json()
        except Exception:
            cardinal.sendMsg(channel, "Error fetching weather data.")
            self.logger.exception(
                "Error fetching forecast for location '{}'".format(location))
            return

        try:
            location = "{}, {}".format(res['name'].strip(),
                                       res['sys']['country'].strip())
        except KeyError:
            cardinal.sendMsg(channel,
                             "Couldn't find weather data for your location.")
            return

        condition = res['weather'][0]['main']
        temperature = int(res['main']['temp'])
        temperature_c = (temperature - 32) * 5 // 9
        humidity = int(res['main']['humidity'])
        winds = float(res['wind']['speed'])
        winds_k = round(winds * 1.609344, 2)
        cardinal.sendMsg(
            channel,
            "[ {} | {} | Temp: {} °F ({} °C) | Humidity: {}% |"
            " Winds: {} mph ({} km/h) ]".format(
                location,
                condition,
                temperature,
                temperature_c,
                humidity,
                winds,
                winds_k)
        )


entrypoint = WeatherPlugin
