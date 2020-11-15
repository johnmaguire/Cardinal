from future import standard_library
standard_library.install_aliases()
from builtins import object
import re
import urllib.request, urllib.error, urllib.parse
import logging

from bs4 import BeautifulSoup

from cardinal.decorators import command, event, help
from cardinal.exceptions import EventRejectedMessage

ARTICLE_URL_REGEX = r"https?://(?:\w{2}\.)?wikipedia\..{2,4}/wiki/(.+)"

DEFAULT_LANGUAGE_CODE = 'en'
DEFAULT_MAX_DESCRIPTION_LENGTH = 150


class WikipediaPlugin(object):
    def __init__(self, cardinal, config):
        """Registers a callback for URL detection."""
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        try:
            self._max_description_length = config['max_description_length']
        except KeyError:
            self.logger.warning("No max description length in config -- using"
                " defaults: %d" % DEFAULT_MAX_DESCRIPTION_LENGTH)
            self._max_description_length = DEFAULT_MAX_DESCRIPTION_LENGTH

        try:
            self._language_code = config['language_code']
        except KeyError:
            self.logger.warning("No language in config -- using defaults: %s" %
                DEFAULT_LANGUAGE_CODE)
            self._language_code = DEFAULT_LANGUAGE_CODE

    def _get_article_info(self, name):
        name = name.replace(' ', '_')
        url = "https://%s.wikipedia.org/wiki/%s" % (
            self._language_code,
            name,
        )

        try:
            uh = urllib.request.urlopen(url)
            soup = BeautifulSoup(uh)
        except Exception as e:
            self.logger.warning(
                "Couldn't query Wikipedia (404?) for: %s" % name, exc_info=True
            )

            return "Unable to find Wikipedia page for: %s" % name

        try:
            # Title of the Wikipedia page
            title = soup.find("h1").get_text()

            # Manipulation to get first paragraph without HTML markup
            content = soup.find_all("div", id="mw-content-text")[0]
            first_paragraph = content.p.get_text()

            if len(first_paragraph) > self._max_description_length:
                first_paragraph = first_paragraph[:self._max_description_length] + \
                    '...'
            else:
                first_paragraph = first_paragraph
        except Exception as e:
            self.logger.error(
                "Error parsing Wikipedia result for: %s" % name,
                exc_info=True
            )

            return "Error parsing Wikipedia result for: %s" % name

        return "[ Wikipedia: %s | %s | %s ]" % (title, first_paragraph, url)

    @event('urls.detection')
    def url_callback(self, cardinal, channel, url):
        match = re.match(ARTICLE_URL_REGEX, url)
        if not match:
            raise EventRejectedMessage

        article_info = self._get_article_info(match.group(1))
        cardinal.sendMsg(channel, article_info)

    @command(['wiki', 'wikipedia'])
    @help("Gets a summary and link to a Wikipedia page")
    @help("Syntax: .wiki <article>")
    def lookup_article(self, cardinal, user, channel, message):
        name = message.split(' ', 1)[1]

        article_info = self._get_article_info(name)
        cardinal.sendMsg(channel, article_info)


def setup(cardinal, config):
    return WikipediaPlugin(cardinal, config)
