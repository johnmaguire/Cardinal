# coding: iso-8859-15 
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

import re
import urllib2
import socket
import HTMLParser

URL_REGEX = re.compile(r"(?:^|\s)((?:www[0-9]{0,3}[.]|https?://)?(?:[a-z0-9]*[.])*(?:[a-z0-9]+[.][a-z]{2,4})(?:/[A-Za-z0-9_.-~:/?\#\[\]@!$&'\(\)*+,;=%]*)?)", flags=re.DOTALL)
TITLE_REGEX = re.compile(r'<title(\s+.*?)?>(.*?)</title>', flags=re.IGNORECASE|re.DOTALL)

class URLsPlugin(object):
    def get_title(self, cardinal, user, channel, msg):
        # Find every URL within the message
        urls = re.findall(URL_REGEX, msg)

        # Loop through the URLs, and make them valid
        for url in urls:
            if url[:7].lower() != "http://" and url[:8].lower() != "https://":
                url = "http://" + url

            # Attempt to load the page, timing out after a default of ten seconds
            try:
                try:
                    timeout = cardinal.config['urls'].TIMEOUT
                except:
                    timeout = 10
                    print "Warning: TIMEOUT not set in urls/config.py."

                o = urllib2.build_opener()
                o.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36')]
                f = o.open(url, timeout=timeout)
            except urllib2.URLError, e:
                print "Unable to load URL (%s): %s" % (url, e.reason)
                return
            except socket.timeout, e:
                print "Unable to load URL (%s): %s" % (url, e.reason)
                return

            # Attempt to find the title, giving up after a default of 512KB
            # (512 * 1024).
            try:
                read_bytes = cardinal.config['urls'].READ_BYTES
            except:
                read_bytes = 512 * 1024
                print "Warning: READ_BYTES not set in urls/config.py."
            
            content_type = f.info()['content-type']
            if not (('text/html' in content_type) or ('text/xhtml' in content_type)):
                return
            content = f.read(read_bytes)
            f.close()
            
            title = re.search(TITLE_REGEX, content)
            if title:
                if len(title.group(2).strip()) > 0:
                    title = re.sub('\s+', ' ', title.group(2)).strip()
                    
                    h = HTMLParser.HTMLParser()
                    title = str(h.unescape(title))
                    
                    cardinal.sendMsg(channel, "URL Found: %s" % title)
                    continue

    get_title.regex = URL_REGEX

def setup():
    return URLsPlugin()
