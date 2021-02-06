import logging
import math

from twisted.internet import defer
from twisted.internet.threads import deferToThread
import requests

from cardinal.decorators import command, help
from cardinal.exceptions import EventRejectedMessage
from cardinal.util import F


class MoviePlugin(object):
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)

        if config is None:
            return

        self.api_key = config.get('api_key', None)

    @command('movie')
    @help('Get the first movie IMDb result for a given search')
    @help('Syntax: .movie <search query>')
    @defer.inlineCallbacks
    def movie(self, cardinal, user, channel, msg):
        yield self.search(cardinal, user, channel, msg, result_type='movie')

    @command('show')
    @help('Get the first TV show IMDb result for a given search')
    @help('Syntax: .show <search query>')
    @defer.inlineCallbacks
    def show(self, cardinal, user, channel, msg):
        yield self.search(cardinal, user, channel, msg, result_type='series')

    @command(['omdb', 'imdb'])
    @help('Get the first IMDb result for a given search')
    @help('Syntax: .imdb <search query>')
    @defer.inlineCallbacks
    def search(self, cardinal, user, channel, msg, result_type=None):
        # Before we do anything, let's make sure we'll be able to query omdb.
        if self.api_key is None:
            cardinal.sendMsg(
                channel,
                "Movie plugin is not configured correctly. Please set API key."
            )
            return

        try:
            search_query = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg("Syntax: .movie <search query>")
            return

        params = {}
        if result_type:
            params['type'] = result_type

        # separate out year if search ends in 4 digits
        if len(search_query) > 5 and search_query[-5] == " " \
                and search_query[-4:].isnumeric():
            params['y'] = search_query[-4:]
            search_query = search_query[:-5]
        params['s'] = search_query

        try:
            result = yield self._form_request(params)
        except Exception:
            cardinal.sendMsg(channel, "Unable to connect to OMDb.")
            self.logger.exception("Failed to connect to OMDb")
            return

        if result['Response'] == 'False':
            if "Error" in result:
                cardinal.sendMsg(channel, result['Error'])
            else:
                cardinal.sendMsg(
                    channel,
                    "An error occurred while attempting to search OMDb.",
                )
                self.logger.error(
                    "Error attempting to search OMDb: %s" % result['Error']
                )
                return

        try:
            movie_id = result['Search'][0]['imdbID']

            params = {
                "i": movie_id,
                "plot": "full",
            }
        # We should never reach this but just in case..
        except IndexError:
            cardinal.sendMsg(channel, "Unable to get movie id.")
            return

        try:
            result = yield self._form_request(params)
        except Exception:
            cardinal.sendMsg(channel, "Unable to connect to OMDb.")
            self.logger.exception("Failed to connect to OMDb.")
            return

        try:
            for message in self._format_data(result):
                cardinal.sendMsg(channel, message)
        except Exception:
            self.logger.exception("Failed to parse info for %s" % movie_id)
            raise EventRejectedMessage

    @defer.inlineCallbacks
    def _form_request(self, payload):
        payload.update({
            'apikey': self.api_key,
            'v': 1,
            'r': 'json',
        })

        return (yield deferToThread(
            requests.get,
            'http://www.omdbapi.com',
            params=payload
        )).json()

    def _format_data(self, data):
        rating = float(data['imdbRating'])
        stars = '\u2b51' * round(rating)
        stars += '.' * (10 - round(rating))

        return [
            "[IMDb] {title} ({year}) - https://imdb.com/title/{movie_id}"
            .format(
                title=F.bold(data['Title']), year=data['Year'],
                movie_id=data['imdbID']
            ),
            "{}: {}  {}: {}".format(
                F.bold("Director"), data['Director'],
                F.bold("Cast"), data['Actors'],
            ),
            "{}: {} [{}]  {}: {}  {}: {}  {}: {}".format(
                F.bold("Rating"), data['imdbRating'], stars,
                F.bold("Runtime"), data['Runtime'],
                F.bold("Genre"), data['Genre'],
                F.bold("Released"), data['Released'],
            ),
            "{}: {}".format(F.bold("Plot"), data['Plot']),
        ]


def setup(cardinal, config):
    return MoviePlugin(cardinal, config)
