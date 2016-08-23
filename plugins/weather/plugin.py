import urllib2
from xml.dom import minidom

YQL_URL = 'https://query.yahooapis.com/v1/public/yql?format=xml&q=%s'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'
WEATHER_QUERY = 'select * from weather.forecast where woeid in (select woeid from geo.places(1) where text="%s")'

class WeatherPlugin(object):
    def get_weather(self, cardinal, user, channel, msg):
        try:
            location = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .weather <location>")
            return

        try:
            url = YQL_URL % urllib2.quote(WEATHER_QUERY % location)
            dom = minidom.parse(urllib2.urlopen(url))
        except urllib2.URLError:
            cardinal.sendMsg(channel, "Error accessing Yahoo! Weather API. (URLError Exception occurred.)")
            return
        except urllib2.HTTPError:
            cardinal.sendMsg(channel, "Error accessing Yahoo! Weather API. (URLError Exception occurred.)")
            return

        try:
            ylocation = dom.getElementsByTagNameNS(WEATHER_NS, 'location')[0]
            yunits = dom.getElementsByTagNameNS(WEATHER_NS, 'units')[0]
            ywind = dom.getElementsByTagNameNS(WEATHER_NS, 'wind')[0]
            yatmosphere = dom.getElementsByTagNameNS(WEATHER_NS, 'atmosphere')[0]
            ycondition = dom.getElementsByTagNameNS(WEATHER_NS, 'condition')[0]

            location_city = str(ylocation.getAttribute('city'))
            location_region = str(ylocation.getAttribute('region'))
            location_country = str(ylocation.getAttribute('country'))

            current_condition = str(ycondition.getAttribute('text'))
            current_temperature = str(ycondition.getAttribute('temp'))
            current_humidity = str(yatmosphere.getAttribute('humidity'))
            current_wind_speed = str(ywind.getAttribute('speed'))

            units_temperature = str(yunits.getAttribute('temperature'))
            units_speed = str(yunits.getAttribute('speed'))
            
            if units_temperature == "F":
                units_temperature2 = "C"
                current_temperature2 = str(int((float(current_temperature) - 32) * float(5)/float(9)))
            else:
                units_temperature2 = "F"
                current_temperature2 = str(int(float(current_temperature) * float(9)/float(5) + 32))

            location = location_city
            if location_region:
                location += ", " + location_region
            if location_country:
                location += ", " + location_country

            cardinal.sendMsg(channel, "[ %s | %s | Temp: %s %s (%s %s) | Humidity: %s%% | Winds: %s %s ]" %
                                                                                   (location,
                                                                                    current_condition,
                                                                                    current_temperature, units_temperature,
                                                                                    current_temperature2, units_temperature2,
                                                                                    current_humidity,
                                                                                    current_wind_speed, units_speed))
        except IndexError:
            cardinal.sendMsg(channel, "Sorry, couldn't find weather for \"%s\"." % location)
            return

    get_weather.commands = ['weather', 'w']
    get_weather.help = ["Retrieves the weather using the Yahoo! weather API.",
                        "Syntax: .weather <location>"]

def setup():
    return WeatherPlugin()
