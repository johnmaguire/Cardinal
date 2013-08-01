# Copyright (c) 2013 John Maguire <john@leftforliving.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation the 
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or 
# sell copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS 
# IN THE SOFTWARE.

import json
import urllib
import urllib2

class YouTubePlugin(object):
    def search(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query YouTube
        if not hasattr(cardinal.config['youtube'], 'API_KEY') or cardinal.config['youtube'].API_KEY == "API_KEY":
            cardinal.sendMsg(channel, "YouTube plugin is not configured correctly. Please set API key.")

        # Grab the search query
        try:
            search_query = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .youtube <search query>")
            return

        yt_request = {'part': 'snippet', 'q': search_query, 'maxResults': 1, 'key': cardinal.config['youtube'].API_KEY}
        uh = urllib2.urlopen("https://www.googleapis.com/youtube/v3/search?" + urllib.urlencode(yt_request))
        content = json.load(uh)

        if 'error' in content:
            cardinal.sendMsg(channel, "An error occurred while attempting to search YouTube.")
            print >> sys.stderr, "ERROR: Error attempting to search YouTube (%s)" % uh
            return

        try:
            title = content['items'][0]['snippet']['title']
            uploader = content['items'][0]['snippet']['channelTitle']
            if len(uploader) == 0:
                uploader = "(not available)"
            video_id = content['items'][0]['id']['videoId']

            cardinal.sendMsg(channel, "[ Title: %s | Uploaded by: %s | https://www.youtube.com/watch?v=%s ]" % (str(title), str(uploader), str(video_id)))
        except IndexError:
            cardinal.sendMsg(channel, "No videos found matching that search.")

    search.commands = ['yt', 'youtube']
    search.help = ["Get the first YouTube result for a given search.",
                   "Syntax: .yt <search query>"]

def setup():
    return YouTubePlugin()
