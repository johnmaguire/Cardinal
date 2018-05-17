import logging, requests

class MoviePlugin(object):
    logger = None
    """Logging object for MoviePlugin."""

    api_key = None
    """Api key for omdb api."""

    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)

        if config is None:
            return

        if "api_key" in config:
            self.api_key = config['api_key']

    def search(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query omdb.
        if self.api_key is None:
            cardinal.sendMsg(channel, "Movie plugin is not configured correctly. Please set API key.")
            return

        try:
            search_query = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg("Syntax: .movie <search_query>")
            return

        params = {'s': search_query, 'type': 'movie'}

        try:
            result = self._form_request(params)
        except Exception, e:
            cardinal.sendMsg(channel, "Unable to connect to omdb.")
            self.logger.exception("Failed to connect to omdb")
            return

        if result['Response'] == 'False':
            if "Error" in result:
                cardinal.sendMsg(channel, bytes(result['Error']))
            else:
                cardinal.sendMsg(channel, "An error occurred while attempting to search omdb.")
                self.logger.error(
                    "Error attempting to search omdb: %s" % content['Error']
                )
                return

        try:
            movie_id = str(result['Search'][0]['imdbID'].encode('utf-8'))

            params = {
                "i": movie_id
            }
        # We should never reach this but just in case..
        except IndexError:
            cardinal.sendMsg(channel, "Unable to get movie id.")
            return

        try:
            result = self._form_request(params)
        except Exception, e:
            cardinal.sendMsg(channel, "Unable to connect to omdb.")
            self.logger.exception("Failed to connect to omdb.")
            return

        try:
            message = self._parse_data(result)
            cardinal.sendMsg(channel, message)
        except Exception, e:
            self.logger.exception("Failed to parse info for %s" % movie_id)
            raise EventRejectedMessage

    search.commands = ['movie', 'omdb', 'imdb']
    search.help = ['Get the first imdb result for a given search.',
                   'Syntax: .movie <search_query>']

    def _form_request(self, payload):
        payload['apikey'] = self.api_key

        return requests.get('http://www.omdbapi.com', params = payload).json()

    def _parse_data(self, data):
        title  = str(data['Title'].encode('utf-8'))
        year   = str(data['Year'].encode('utf-8'))
        rating = str(data['imdbRating'].encode('utf-8'))
        genre  = str(data['Genre'].encode('utf-8'))
    #   plot   = str(data['Plot'].encode('utf-8'))

        movie_id = str(data['imdbID'].encode('utf-8'))

        return ("[ Title: %s | Year: %s | Rating: %s | Genre: %s | http://imdb.com/title/%s ]" %
            (title, year, rating, genre, movie_id))

def setup(cardinal, config):
    return MoviePlugin(cardinal, config)
