import datetime
import re
import logging

import requests
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from cardinal.decorators import command, event, help
from cardinal.exceptions import EventRejectedMessage

VIDEO_URL_REGEX = re.compile(r'https?:\/\/(?:www\.)?youtube\..{2,4}\/watch\?.*(?:v=(.+?))(?:(?:&.*)|$)', flags=re.IGNORECASE)  # noqa: E501
VIDEO_URL_SHORT_REGEX = re.compile(r'https?:\/\/(?:www\.)?youtu\.be\/(.+?)(?:(?:\?.*)|$)', flags=re.IGNORECASE)  # noqa: E501


# The following two functions were borrowed from Stack Overflow:
# https://stackoverflow.com/a/64232786/242129
def get_isosplit(s, split):
    if split in s:
        n, s = s.split(split)
    else:
        n = 0
    return n, s


def parse_isoduration(s):
    # Remove prefix
    s = s.split('P')[-1]

    # Step through letter dividers
    days, s = get_isosplit(s, 'D')
    _, s = get_isosplit(s, 'T')
    hours, s = get_isosplit(s, 'H')
    minutes, s = get_isosplit(s, 'M')
    seconds, s = get_isosplit(s, 'S')

    # Convert all to seconds
    dt = datetime.timedelta(
        days=int(days),
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
    )
    return dt


class YouTubePlugin:
    logger = None
    """Logging object for YouTubePlugin"""

    api_key = None
    """API key for Youtube API"""

    def __init__(self, cardinal, config):
        # Initialize logging
        self.logger = logging.getLogger(__name__)

        if config is None:
            return

        if 'api_key' in config:
            self.api_key = config['api_key']

    @command(['youtube', 'yt'])
    @help("Get the first YouTube result for a given search.")
    @help("Syntax: .youtube <search query>")
    @defer.inlineCallbacks
    def search(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query YouTube
        if self.api_key is None:
            cardinal.sendMsg(
                channel,
                "YouTube plugin is not configured correctly. "
                "Please set API key."
            )

        # Grab the search query
        try:
            search_query = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .youtube <search query>")
            return

        try:
            result = yield self._search(search_query)
        except Exception:
            self.logger.exception("Failed to search YouTube")
            cardinal.sendMsg(channel, "Error while searching YouTube")
            return

        if result is None:
            cardinal.sendMsg(channel, "No videos found matching that search.")
            return

        try:
            message = yield self._get_formatted_details(
                result['id']['videoId']
            )
        except Exception:
            self.logger.exception("Error finding search result details")
            cardinal.sendMsg(channel, "Error while searching YouTube")
            return

        cardinal.sendMsg(channel, message)

    @defer.inlineCallbacks
    def _get_formatted_details(self, video_id):
        params = {
            'id': video_id,
            'maxResults': 1,
            'part': 'snippet,statistics,contentDetails'
        }

        result = (yield self._form_request("videos", params))['items'][0]
        return self._parse_item(result)

    @defer.inlineCallbacks
    def _search(self, search_query):
        params = {
            'q': search_query,
            'part': 'snippet',
            'maxResults': 1,
            'type': 'video',
        }

        result = yield self._form_request("search", params)

        if 'error' in result:
            raise Exception("Error searching Youtube: %s" % result['error'])

        try:
            return result['items'][0]
        except IndexError:
            return None

    @event('urls.detection')
    @defer.inlineCallbacks
    def _get_video_info(self, cardinal, channel, url):
        match = re.match(VIDEO_URL_REGEX, url)
        if not match:
            match = re.match(VIDEO_URL_SHORT_REGEX, url)
        if not match:
            raise EventRejectedMessage

        video_id = match.group(1)
        params = {
            'id': video_id,
            'maxResults': 1,
            'part': 'snippet,statistics,contentDetails',
        }

        try:
            result = yield self._form_request("videos", params)
        except Exception:
            self.logger.exception("Failed to fetch info for %s'" % video_id)
            raise EventRejectedMessage

        try:
            message = self._parse_item(result['items'][0])
            cardinal.sendMsg(channel, message)
        except Exception:
            self.logger.exception("Failed to parse info for %s'" % video_id)
            raise EventRejectedMessage

    @defer.inlineCallbacks
    def _form_request(self, endpoint, params):
        # Add API key to all requests
        params['key'] = self.api_key

        r = yield deferToThread(
            requests.get,
            "https://www.googleapis.com/youtube/v3/" + endpoint,
            params=params,
        )

        return r.json()

    def _parse_item(self, item):
        title = str(item['snippet']['title'])
        views = int(item['statistics']['viewCount'])
        uploader = str(item['snippet']['channelTitle'])
        if len(uploader) == 0:
            uploader = "(not available)"
        dt = parse_isoduration(item['contentDetails']['duration'])

        video_id = str(item['id'])
        
        # Check if video's categoryId is 10 (Music)
        category = int(item['snippet']['categoryId'])
        if category == 10:
            title = '♫ ' + title + ' ♫'

        message_parts = [
            "Title: {}".format(title),
            "Uploaded by: {}".format(uploader),
            "Duration: {}".format(dt),
            "{:,} views".format(views),
            "https://youtube.com/watch?v={}".format(video_id),
        ]
        return "[ {} ]".format(' | '.join(message_parts))


entrypoint = YouTubePlugin
