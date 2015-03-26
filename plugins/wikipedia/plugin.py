import re
import urllib2
import logging

from bs4 import BeautifulSoup

from cardinal.exceptions import EventRejectedMessage

ARTICLE_URL_REGEX = "https?:\/\/(?:\w{2}\.)?wikipedia\..{2,4}\/wiki\/(.+)"

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

        self._callback_id = cardinal.event_manager.register_callback(
            'urls.detection', self.url_callback)

    def _get_article_info(self, name):
        name = name.replace(' ', '_')
        url = "https://%s.wikipedia.org/wiki/%s" % (self._language_code, name)

        try:
            uh = urllib2.urlopen(url)
            soup = BeautifulSoup(uh)
        except Exception, e:
            self.logger.warning(
                "Couldn't query Wikipedia (404?) for: %s" % name, exc_info=True
            )

            return "Unable to find Wikipedia page for: %s" % name

        try:
            # Title of the Wikipedia page
            title = str(soup.find("h1").contents[0])

            # Manipulation to get first paragraph without HTML markup
            content = soup.find_all("div", id="mw-content-text")[0]
            first_paragraph = content.p
            for tag in content.p.find_all():
                tag.unwrap()
            first_paragraph = str(first_paragraph)[3:-4]

            if len(first_paragraph) > self._max_description_length:
                first_paragraph = (first_paragraph[:self._max_description_length] +
                    '...')
        except Exception, e:
            self.logger.error(
                "Error parsing Wikipedia result for: %s" % name,
                exc_info=True
            )

            return "Error parsing Wikipedia result for: %s" % name

        return str(
            "[ Wikipedia: %s | %s | %s ]" % (title, first_paragraph, url))

    def url_callback(self, cardinal, channel, url):
        match = re.match(ARTICLE_URL_REGEX, url)
        if not match:
            raise EventRejectedMessage

        article_info = self._get_article_info(match.group(1))
        cardinal.sendMsg(channel, article_info)

    def lookup_article(self, cardinal, user, channel, message):
        name = message.split(' ', 1)[1]

        article_info = self._get_article_info(name)
        cardinal.sendMsg(channel, article_info)

    lookup_article.commands = ['wiki', 'wikipedia']
    lookup_article.help = ["Gets a summary and link to a Wikipedia page",
                           "Syntax: .wiki <article>"]

    def close(self, cardinal):
        """Removes registered callback."""
        cardinal.event_manager.remove_callback(
            "urls.detection", self._callback_id)

def setup(cardinal, config):
    return WikipediaPlugin(cardinal, config)
