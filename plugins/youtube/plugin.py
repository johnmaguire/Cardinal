import re
import json
import urllib
import urllib2
import logging

from cardinal.exceptions import EventRejectedMessage

VIDEO_URL_REGEX = re.compile(r'https?:\/\/(?:www\.)?youtube\..{2,4}\/watch\?.*(?:v=(.+?))(?:(?:&.*)|$)', flags=re.IGNORECASE)
VIDEO_URL_SHORT_REGEX = re.compile(r'https?:\/\/(?:www\.)?youtu\.be\/(.+?)(?:(?:\?.*)|$)', flags=re.IGNORECASE)


class YouTubePlugin(object):
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

        self.callback_id = cardinal.event_manager.register_callback(
            'urls.detection', self._get_video_info
        )

    def search(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query YouTube
        if self.api_key is None:
            cardinal.sendMsg(channel, "YouTube plugin is not configured correctly. Please set API key.")

        # Grab the search query
        try:
            search_query = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .youtube <search query>")
            return

        params = {'q': search_query, 'part': 'snippet', 'maxResults': 1, 'type': 'video'}

        try:
            result = self._form_request("search", params)
        except Exception, e:
            cardinal.sendMsg(channel, "Unable to connect to YouTube.")
            self.logger.exception("Failed to connect to YouTube")
            return

        if 'error' in result:
            cardinal.sendMsg(channel, "An error occurred while attempting to search YouTube.")
            self.logger.error(
                "Error attempting to search YouTube: %s" % content['error']
            )
            return

        try:
            video_id = str(result['items'][0]['id']['videoId'].encode('utf-8'))

            params = {
                'id': video_id,
                'maxResults': 1,
                'part': 'snippet,statistics'
            }
        except IndexError:
            cardinal.sendMsg(channel, "No videos found matching that search.")
            return

        try:
            result = self._form_request("videos", params)
        except Exception, e:
            cardinal.sendMsg(channel, "Unable to connect to YouTube.")
            self.logger.exception("Failed to connect to YouTube")
            return

        try:
            message = self._parse_item(result['items'][0])
            cardinal.sendMsg(channel, message)
        except IndexError:
            cardinal.sendMsg(channel, "No videos found matching that search.")
        except Exception, e:
            self.logger.exception("Failed to parse info for %s'" % video_id)
            raise EventRejectedMessage

    search.commands = ['youtube', 'yt']
    search.help = ["Get the first YouTube result for a given search.",
                   "Syntax: .youtube <search query>"]

    def _get_video_info(self, cardinal, channel, url):
        match = re.match(VIDEO_URL_REGEX, url)
        if not match:
            match = re.match(VIDEO_URL_SHORT_REGEX, url)
        if not match:
            raise EventRejectedMessage

        video_id = match.group(1)
        params = {'id': video_id, 'maxResults': 1, 'part': 'snippet,statistics'}

        try:
            result = self._form_request("videos", params)
        except Exception, e:
            self.logger.exception("Failed to fetch info for %s'" % video_id)
            raise EventRejectedMessage

        try:
            message = self._parse_item(result['items'][0])
            cardinal.sendMsg(channel, message)
        except Exception, e:
            self.logger.exception("Failed to parse info for %s'" % video_id)
            raise EventRejectedMessage

    def _form_request(self, endpoint, params):
        # Add API key to all requests
        params['key'] = self.api_key

        # Make request to specified endpoint and return JSON decoded result
        uh = urllib2.urlopen("https://www.googleapis.com/youtube/v3/" +
            endpoint + "?" +
            urllib.urlencode(params))

        return json.load(uh)

    def _parse_item(self, item):
        title = str(item['snippet']['title'].encode('utf-8'))
        views = int(item['statistics']['viewCount'].encode('utf-8'))
        uploader = str(item['snippet']['channelTitle'].encode('utf-8'))
        if len(uploader) == 0:
            uploader = "(not available)"

        # TODO: Verify no videos return the ID as item['id']['videoId']
        # (Hint: If this breaks, that's probably why.)
        video_id = str(item['id'].encode('utf-8'))

        return ("[ Title: %s | Uploaded by: %s | %s views | https://www.youtube.com/watch?v=%s ]" %
                (title, uploader, "{:,}".format(views), video_id))

    def close(self, cardinal):
        cardinal.event_manager.remove_callback('urls.detection', self.callback_id)

def setup(cardinal, config):
    return YouTubePlugin(cardinal, config)
