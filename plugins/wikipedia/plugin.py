import re
import logging

import requests
from bs4 import BeautifulSoup
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from cardinal.decorators import command, event, help
from cardinal.exceptions import EventRejectedMessage

ARTICLE_URL_REGEX = r"https?://(?:\w{2}\.)?wikipedia\..{2,4}/wiki/(.+)"

DEFAULT_LANGUAGE_CODE = 'en'
DEFAULT_MAX_DESCRIPTION_LENGTH = 150


# This is used to filter out blank paragraphs
def class_is_not_mw_empty_elt(css_class):
    return css_class != 'mw-empty-elt'


class WikipediaPlugin:
    def __init__(self, cardinal, config):
        """Registers a callback for URL detection."""
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        try:
            self._max_description_length = config['max_description_length']
        except KeyError:
            self.logger.warning(
                "No max description length in config -- using defaults: %d" %
                DEFAULT_MAX_DESCRIPTION_LENGTH
            )
            self._max_description_length = DEFAULT_MAX_DESCRIPTION_LENGTH

        try:
            self._language_code = config['language_code']
        except KeyError:
            self.logger.warning(
                "No language in config -- using defaults: %s" %
                DEFAULT_LANGUAGE_CODE
            )
            self._language_code = DEFAULT_LANGUAGE_CODE

    @defer.inlineCallbacks
    def _get_article_info(self, name):
        url = "https://%s.wikipedia.org/wiki/%s" % (
            self._language_code,
            name.replace(' ', '_'),
        )

        try:
            r = yield deferToThread(requests.get, url)
            url = r.url
            soup = BeautifulSoup(r.text, features="html.parser")
        except Exception:
            self.logger.warning(
                "Couldn't query Wikipedia (404?) for: %s" % name, exc_info=True
            )

            return "Unable to find Wikipedia page for: %s" % name

        try:
            # Title of the Wikipedia page
            title = soup.find("h1").get_text()

            # Manipulation to get first paragraph without HTML markup
            disambiguation = soup.find("table", id="disambigbox") is not None
            if disambiguation:
                summary = "Disambiguation Page"
            else:
                content = soup.find_all("div", id="mw-content-text")[0]
                for x in content.find_all(
                            "p",
                            class_=class_is_not_mw_empty_elt,
                        ):
                    if len(x.get_text(strip=True)) != 0:
                        first_paragraph = x.get_text(strip=True)
                        break

                if len(first_paragraph) > self._max_description_length:
                    summary = "{}...".format(
                        first_paragraph[:self._max_description_length].strip()
                    )
                else:
                    summary = first_paragraph
        except Exception:
            self.logger.error(
                "Error parsing Wikipedia result for: %s" % name,
                exc_info=True
            )

            return "Error parsing Wikipedia result for: %s" % name

        return "Wikipedia: %s - %s - %s" % (title, summary, url)

    @event('urls.detection')
    @defer.inlineCallbacks
    def url_callback(self, cardinal, channel, url):
        match = re.match(ARTICLE_URL_REGEX, url)
        if not match:
            raise EventRejectedMessage

        article_info = yield self._get_article_info(match.group(1))
        cardinal.sendMsg(channel, article_info)

    @command(['wiki', 'wikipedia'])
    @help("Gets a summary and link to a Wikipedia page")
    @help("Syntax: .wiki <article>")
    @defer.inlineCallbacks
    def lookup_article(self, cardinal, user, channel, message):
        name = message.split(' ', 1)[1]

        article_info = yield self._get_article_info(name)
        cardinal.sendMsg(channel, article_info)


entrypoint = WikipediaPlugin
