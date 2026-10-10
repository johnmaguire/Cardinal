from unittest.mock import Mock, patch

import pytest
import pytest_twisted
import requests

from cardinal.bot import CardinalBot, user_info
from cardinal.unittest_util import get_mock_db
from plugins.weather.plugin import WeatherPlugin


@pytest.fixture
def cardinal():
    bot = Mock(spec=CardinalBot)
    bot.get_db, database = get_mock_db()
    database['reader'] = 'London'
    return bot


@pytest.fixture
def user():
    return user_info('reader', 'reader', 'localhost')


@pytest.mark.parametrize('config', [
    None,
    {'provider': 'openweather'},
    {'provider': 'weatherapi', 'api_key': None},
])
@pytest.mark.parametrize('message,has_saved_location', [
    ('.weather London', True),
    ('.weather', True),
    ('.weather', False),
])
@pytest_twisted.inlineCallbacks
def test_missing_api_key(cardinal, user, config, message, has_saved_location):
    plugin = WeatherPlugin(cardinal, config)
    if not has_saved_location:
        with plugin.db() as database:
            database.clear()

    with patch('requests.get', side_effect=requests.HTTPError('No credentials')) \
            as mock_get:
        yield plugin.weather(cardinal, user, '#test', message)

    mock_get.assert_not_called()
    cardinal.sendMsg.assert_called_once_with(
        '#test',
        'Weather plugin is not configured correctly. Please set API key.'
    )


@pytest.mark.parametrize('provider,response_body,key_parameter', [
    ('weatherapi', {
        'location': {'name': 'London', 'region': '', 'country': 'GB'},
        'current': {
            'condition': {'text': 'Clear'},
            'temp_f': 50,
            'humidity': 41,
            'wind_mph': 5.0,
        },
    }, 'key'),
    ('openweather', {
        'name': 'London',
        'sys': {'country': 'GB'},
        'weather': [{'main': 'Clear'}],
        'main': {'temp': 50, 'humidity': 41},
        'wind': {'speed': 5.0},
    }, 'appid'),
])
@pytest.mark.parametrize('message', ['.weather London', '.weather'])
@pytest_twisted.inlineCallbacks
def test_configured_weather(cardinal, user, provider, response_body,
                            key_parameter, message):
    plugin = WeatherPlugin(cardinal, {'provider': provider, 'api_key': 'test'})
    response = Mock()
    response.json.return_value = response_body

    with patch('requests.get', return_value=response) as mock_get:
        yield plugin.weather(cardinal, user, '#test', message)

    mock_get.assert_called_once()
    params = mock_get.call_args.kwargs['params']
    assert params['q'] == 'London'
    assert params[key_parameter] == 'test'
    cardinal.sendMsg.assert_called_once_with(
        '#test',
        '[ London, GB | Clear | Temp: 50 °F (10.0 °C) | Humidity: 41% |'
        ' Winds: 5.0 mph (8.05 km/h) ]'
    )


@pytest.mark.parametrize('provider', ['weatherapi', 'openweather'])
@pytest_twisted.inlineCallbacks
def test_configured_weather_without_location(cardinal, user, provider):
    plugin = WeatherPlugin(cardinal, {'provider': provider, 'api_key': 'test'})
    with plugin.db() as database:
        database.clear()

    with patch('requests.get') as mock_get:
        yield plugin.weather(cardinal, user, '#test', '.weather')

    mock_get.assert_not_called()
    cardinal.sendMsg.assert_called_once_with(
        '#test',
        'Syntax: .weather <location> (.setw <location> to make it permanent)'
    )


@pytest.mark.parametrize('provider', ['weatherapi', 'openweather'])
@pytest_twisted.inlineCallbacks
def test_configured_weather_request_error(cardinal, user, provider):
    plugin = WeatherPlugin(cardinal, {'provider': provider, 'api_key': 'test'})

    with patch('requests.get', side_effect=requests.HTTPError('Offline')) \
            as mock_get:
        yield plugin.weather(cardinal, user, '#test', '.weather London')

    mock_get.assert_called_once()
    cardinal.sendMsg.assert_called_once_with(
        '#test', 'Error fetching weather data.'
    )
