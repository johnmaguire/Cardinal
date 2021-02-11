import logging

from twisted.internet import defer
from twisted.internet.threads import deferToThread
import requests

from cardinal.decorators import command, help
from cardinal.exceptions import EventRejectedMessage
from cardinal.util import F


def format_data_short(data):
    if data['imdbRating'] == "N/A":
        rating = ""
    else:
        rating = "Rating: {} | ".format(float(data['imdbRating']))

    return "[ IMDb: {title} ({year}) - {runtime} | {maybe_rating}Plot: {plot} | {link} ]".format(  # noqa: E501
        title=data['Title'],
        year=data['Year'],
        runtime=data['Runtime'],
        maybe_rating=rating,
        plot=data['Plot'],
        link="https://imdb.com/title/{}".format(data['imdbID']),
    )


def format_data_full(data):
    if data['imdbRating'] == "N/A":
        maybe_rating = ""
    else:
        rating = float(data['imdbRating'])
        stars = '*' * round(rating)
        stars += '.' * (10 - round(rating))

        maybe_rating = "{}: {} [{}]  ".format(
            F.bold("Rating"), data['imdbRating'], stars
        )

    return [
        "[IMDb] {title} ({year}) - https://imdb.com/title/{movie_id}"
        .format(
            title=F.bold(data['Title']), year=data['Year'],
            movie_id=data['imdbID']
        ),
        "{}{}: {}  {}: {}  {}: {}".format(
            maybe_rating,
            F.bold("Runtime"), data['Runtime'],
            F.bold("Genre"), data['Genre'],
            F.bold("Released"), data['Released'],
        ),
        "{}: {}  {}: {}".format(
            F.bold("Director"), data['Director'],
            F.bold("Cast"), data['Actors'],
        ),
        "{}: {}".format(F.bold("Plot"), data['Plot']),
    ]


class MoviePlugin(object):
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)
        self.cardinal = cardinal

        if config is None:
            raise Exception("Movie plugin requires configuration")

        self.api_key = config.get('api_key', None)
        self.default_output = config.get('default_output', 'short')
        self.private_output = config.get('private_output', 'full')
        self.channels = config.get('channels', {})

    def get_output_format(self, channel):
        chantypes = self.cardinal.supported.getFeature("CHANTYPES") or ('#',)
        if channel[0] not in chantypes:
            return self.private_output

        # Fetch channel-specific output format, or default
        return self.channels.get(channel, {}) \
            .get('output', self.default_output)

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
            search_query = msg.split(' ', 1)[1].strip()
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
                "plot": self.get_output_format(channel),
            }
        except IndexError:
            cardinal.sendMsg(channel, "Error parsing result.")
            self.logger.exception("Failure parsing result: {}".format(result))
            return

        try:
            result = yield self._form_request(params)
        except Exception:
            cardinal.sendMsg(channel, "Unable to connect to OMDb.")
            self.logger.exception("Failed to connect to OMDb.")
            return

        try:
            for message in self._format_data(channel, result):
                cardinal.sendMsg(channel, message)
        except Exception:
            cardinal.sendMsg(channel, "Error parsing result.")
            self.logger.exception("Failed to parse info for %s", movie_id)
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
            'https://www.omdbapi.com',
            params=payload
        )).json()

    def _format_data(self, channel, data):
        if self.get_output_format(channel) == 'short':
            return [format_data_short(data)]
        else:
            return format_data_full(data)


entrypoint = MoviePlugin
