import logging
import re
from urllib.parse import urlparse

from twisted.internet import defer
from twisted.internet.threads import deferToThread
import requests

from cardinal.decorators import command, event, help
from cardinal.exceptions import EventRejectedMessage
from cardinal.util import F

_indexes = {1: 'a', 2: 'b', 3: 'c', 4: 'd', 5: 'e'}
_numerals = {v: k for k, v in _indexes.items()}


class SearchCache:
    def __init__(self, max_length):
        self.max_length = max_length

        self._cache = dict()
        self._keys = list()

    def add(self, channel, results):
        # don't duplicate channel in list
        try:
            self._keys.remove(channel)
        except ValueError:
            pass

        self._keys.append(channel)
        self._cache[channel] = results

        # remove oldest item in list
        while len(self._keys) > self.max_length:
            key = self._keys.pop(0)
            del self._cache[key]

    def get(self, channel):
        return self._cache[channel]


def get_imdb_link(id):
    return "https://imdb.com/title/{}".format(id)


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
        link=get_imdb_link(data['imdbID']),
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

    link = get_imdb_link(data['imdbID'])
    return [
        "[IMDb] {title} ({year}) - {link}"
        .format(
            title=F.bold(data['Title']),
            year=data['Year'],
            link=link
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


class MoviePlugin:
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)
        self.cardinal = cardinal

        if config is None:
            raise Exception("Movie plugin requires configuration")

        self.api_key = config.get('api_key', None)
        self.default_output = config.get('default_output', 'short')
        self.private_output = config.get('private_output', 'full')
        self.channels = config.get('channels', {})
        self.max_search_results = config.get('max_search_results', 5)
        if self.max_search_results > 5:
            raise Exception("max_search_results must be between 1-5")

        # Stores results for quick lookup
        self._search_cache = SearchCache(5)

    def search_allowed(self, channel):
        chantypes = self.cardinal.supported.getFeature("CHANTYPES") or ('#',)
        if channel[0] not in chantypes:
            return True

        return self.channels.get(channel, {}) \
            .get('allow_search', False)

    def get_output_format(self, channel):
        chantypes = self.cardinal.supported.getFeature("CHANTYPES") or ('#',)
        if channel[0] not in chantypes:
            return self.private_output

        # Fetch channel-specific output format, or default
        return self.channels.get(channel, {}) \
            .get('output', self.default_output)

    @command('movie')
    @help('Get the first movie IMDb result for a given search')
    @help('Syntax: @movie <search query>')
    @defer.inlineCallbacks
    def movie(self, cardinal, user, channel, msg):
        yield self.imdb(cardinal, user, channel, msg, result_type='movie')

    @command('show')
    @help('Get the first TV show IMDb result for a given search')
    @help('Syntax: @show <search query>')
    @defer.inlineCallbacks
    def show(self, cardinal, user, channel, msg):
        yield self.imdb(cardinal, user, channel, msg, result_type='series')

    @command(['omdb', 'imdb'])
    @help('Get the first IMDb result for a given search')
    @help('Syntax: @imdb <search query>')
    @defer.inlineCallbacks
    def imdb(self, cardinal, user, channel, msg, result_type=None):
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
            command = 'imdb'
            if result_type == 'series':
                command = 'show'
            elif result_type == 'movie':
                command = 'movie'
            cardinal.sendMsg(channel, f"Syntax: .{command} <search query>")
            return

        # first, check if this is just an IMDB id
        imdb_id = None
        if re.match(r'^tt\d{7,8}$', search_query):
            imdb_id = search_query
        # next, check if this is is a search selection
        elif search_query.isnumeric() \
                and int(search_query) in _indexes:
            try:
                res_id = int(search_query) - 1
                res = self._search_cache.get(channel)[res_id]
            except KeyError:
                pass
            else:
                imdb_id = res['imdbID']
        elif search_query in _numerals:
            try:
                res_id = _numerals[search_query] - 1
                res = self._search_cache.get(channel)[res_id]
            except KeyError:
                pass
            else:
                imdb_id = res['imdbID']

        # otherwise, try to find the best match
        if not imdb_id:
            try:
                results = yield self._search(search_query, result_type)
                imdb_id = results[0]['imdbID']
            except RuntimeError as e:
                cardinal.sendMsg(channel, str(e))
                return
            except Exception:
                self.logger.exception("Unknown error while searching")
                return

        try:
            yield self._send_result(cardinal, channel, imdb_id)
        except Exception:
            cardinal.sendMsg(channel, "Error fetching movie info.")
            self.logger.exception("Failed to parse info for %s", imdb_id)
            return

    @command('search')
    @help('Return IMDb search results (use .imdb for a single title)')
    @help('Syntax: @search <search query>')
    @defer.inlineCallbacks
    def search(self, cardinal, user, channel, msg):
        if self.api_key is None:
            cardinal.sendMsg(
                channel,
                "Movie plugin is not configured correctly. Please set API key."
            )
            return

        if not self.search_allowed(channel):
            cardinal.sendMsg(channel,
                             "Movie search is not allowed in this channel. "
                             "Try messaging me directly.")
            return

        try:
            search_query = msg.split(' ', 1)[1].strip()
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .search <search query>")
            return

        try:
            results = yield self._search(search_query)
        except RuntimeError as e:
            cardinal.sendMsg(channel, str(e))
            return
        if not results:
            cardinal.sendMsg(channel, "No results found.")
            return

        # Store these for quick lookup in imdb command
        self._search_cache.add(channel, results)

        i = 0
        for result in results:
            i += 1
            type_ = result['Type'].capitalize()
            link = get_imdb_link(result['imdbID'])
            cardinal.sendMsg(
                channel,
                f"{i}. {result['Title']} ({result['Year']})  "
                f"[{type_}] - {link}"
            )
            if i >= self.max_search_results:
                break

        cardinal.sendMsg(
            channel,
            "Use .imdb <numeral> to view more. (1/a, 2/b, etc.)"
        )

    @defer.inlineCallbacks
    def _search(self, search_query, result_type=None):
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
            self.logger.exception("Unable to connect to OMDb")
            raise RuntimeError("Failed to connect to OMDb")

        if result['Response'] == 'False':
            if "Error" in result:
                self.logger.error(
                    "Error attempting to search OMDb: %s" % result['Error']
                )

            raise RuntimeError("Error searching OMDb: %s" % result['Error'])

        return result['Search']

    @defer.inlineCallbacks
    def _send_result(self, cardinal, channel, imdb_id):
        params = {
            "i": imdb_id,
            "plot": self.get_output_format(channel),
        }

        result = yield self._form_request(params)

        for message in self._format_data(channel, result):
            cardinal.sendMsg(channel, message)

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

    @event('urls.detection')
    @defer.inlineCallbacks
    def imdb_handler(self, cardinal, channel, url):
        if self.api_key is None:
            raise EventRejectedMessage

        o = urlparse(url)

        if o.netloc not in ('imdb.com', 'www.imdb.com'):
            raise EventRejectedMessage

        match = re.match(r'^/title/(tt\d{7,8})(?:$|/.*)', o.path)
        if not match:
            raise EventRejectedMessage

        try:
            yield self._send_result(cardinal, channel, match.group(1))
        except Exception:
            self.logger.exception("Error parsing IMDB ID %s", match.group(1))
            raise EventRejectedMessage


entrypoint = MoviePlugin
