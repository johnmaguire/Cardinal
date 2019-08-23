# coding: iso-8859-15
from __future__ import absolute_import, print_function, division
import re
import urllib2
import socket
import HTMLParser
import logging
from datetime import datetime

from twisted.internet import defer

from cardinal.decorators import regex

URL_REGEX = re.compile(r"(?:^|\s)((?:https?://)?(?:[a-z0-9.\-]+[.][a-z]{2,4}/?"
                       r")(?:[^\s()<>]*|\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\)"
                       r")+(?:\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\)|[^\s`!()"
                       r"\[\]{};:\'\".,<>?]))",
                       flags=re.IGNORECASE | re.DOTALL)
TITLE_REGEX = re.compile(r'<title(\s+.*?)?>(.*?)</title>',
                         flags=re.IGNORECASE | re.DOTALL)


class URLsPlugin(object):
    TIMEOUT = 10
    """Timeout in seconds before bailing on loading page"""

    READ_BYTES = 524288
    """Bytes to read before bailing on loading page (512KB)"""

    LOOKUP_COOLOFF = 10
    """Timeout in seconds before looking up the same URL again"""

    def __init__(self, cardinal, config):
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Holds the last URL looked up, for cooloff
        self.last_url = None

        # Holds time last URL was looked up, for cooloff
        self.last_url_at = None

        # If config doesn't exist, use an empty dict
        config = config or {}

        self.timeout = config.get('timeout', self.TIMEOUT)
        self.read_bytes = config.get('read_bytes', self.READ_BYTES)
        self.lookup_cooloff = config.get('lookup_cooloff', self.LOOKUP_COOLOFF)

        cardinal.event_manager.register('urls.detection', 2)

    @regex(URL_REGEX)
    @defer.inlineCallbacks
    def get_title(self, cardinal, user, channel, msg):
        # Find every URL within the message
        urls = re.findall(URL_REGEX, msg)

        # Loop through the URLs, and make them valid
        for url in urls:
            if url[:7].lower() != "http://" and url[:8].lower() != "https://":
                url = "http://" + url

            if (url == self.last_url and self.last_url_at and
                    (datetime.now() - self.last_url_at).seconds <
                    self.lookup_cooloff):
                defer.returnValue(None)

            self.last_url = url
            self.last_url_at = datetime.now()

            # Check if another plugin has hooked into this URL and wants to
            # provide information itself
            hooked = yield cardinal.event_manager.fire(
                'urls.detection', channel, url)

            if hooked:
                defer.returnValue(None)

            # FIXME: Replace with Twisted call
            try:
                o = urllib2.build_opener()
                # User agent helps combat some bot checks
                o.addheaders = [
                    ('User-agent', 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36')
                ]
                f = o.open(url, timeout=self.timeout)
            except Exception, e:
                self.logger.exception("Unable to load URL: %s" % url)
                defer.returnValue(None)

            # Attempt to find the title
            content_type = f.info()['content-type']
            if not ('text/html' in content_type or
                    'text/xhtml' in content_type):
                defer.returnValue(None)
            content = f.read(self.read_bytes)
            f.close()

            title = re.search(TITLE_REGEX, content)
            if title:
                if len(title.group(2).strip()) > 0:
                    title = re.sub('\s+', ' ', title.group(2)).strip()

                    h = HTMLParser.HTMLParser()

                    title = str(h.unescape(title).encode('utf-8'))

                    # Truncate long titles to the first 200 characters.
                    title_to_send = title[:200] if len(title) >= 200 else title

                    cardinal.sendMsg(channel, "URL Found: %s" % title_to_send)
                    continue

    def close(self, cardinal):
        cardinal.event_manager.remove('urls.detection')

def setup(cardinal, config):
    return URLsPlugin(cardinal, config)
