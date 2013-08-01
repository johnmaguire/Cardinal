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

import sys
import ast
import json
import urllib
import urllib2

class CalculatorPlugin(object):
    def _parse_data(self, data):
        d = {}

        for pair in data[1:-1].split(','):
            (k, v) = pair.split(':')

            v = v.strip()
            if v == "true":
                v = "True"
            elif v == "false":
                v = "False"

            try:
                v = ast.literal_eval(v)
            except:
                print >> sys.stderr, "ERROR: Unable to evaluate Google calculator API value (%s)" % v
                raise

            d[k] = v

        return d

    def calculate(self, cardinal, user, channel, msg):
        # Grab the search query
        try:
            search_query = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .calc <query>")
            return

        try:
            c_request = {'hl': 'en', 'q': search_query}
            uh = urllib2.urlopen("https://www.google.com/ig/calculator?" + urllib.urlencode(c_request))
        except urllib2.URLError, e:
            cardinal.sendMsg(channel, "Unable to reach Google calculator.")
            print >> sys.stderr, "ERROR: Failed to reach the server: %s" % e.reason
            return
        except urllib2.HTTPError, e:
            cardinal.sendMsg(channel, "Unable to access Google calculator API.")
            print >> sys.stderr, "ERROR: The server did not fulfill the request. (%s Error)" % e.code
            return

        try:
            content = self._parse_data(uh.read())
        except:
            cardinal.sendMsg(channel, "Error parsing Google calculator API data.")

        if 'error' in content and content['error']:
            cardinal.sendMsg(channel, "Unable to perform calculation: %s." % content['error'])
            return

        try:
            question = content['lhs']
            response = content['rhs']

            cardinal.sendMsg(channel, "%s = %s" % (str(question), str(response)))
        except IndexError:
            cardinal.sendMsg(channel, "An error occurred while processing the calculation.")

    calculate.commands = ['calc', 'c', 'calculate']
    calculate.help = ["Calculate using Google calculator.",
                      "Syntax: .calc <query>"]

def setup():
    return CalculatorPlugin()
