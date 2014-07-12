import sys
import json
import urllib
import urllib2

class CalculatorPlugin(object):
    def calculate(self, cardinal, user, channel, msg):
        # Grab the search query
        try:
            question = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .calc <query>")
            return

        try:
            c_request = {'question': question}
            uh = urllib2.urlopen("http://dib.leftforliving.com:8080/query?" + urllib.urlencode(c_request))
        except urllib2.URLError, e:
            cardinal.sendMsg(channel, "Unable to reach evaluation server.")
            print >> sys.stderr, "ERROR: Failed to reach the server: %s" % e.reason
            return
        except urllib2.HTTPError, e:
            cardinal.sendMsg(channel, "Unable to reach evaluation server.")
            print >> sys.stderr, "ERROR: The server did not fulfill the request. (%s Error)" % e.code
            return

        try:
            response = json.load(uh)
        except:
            cardinal.sendMsg(channel, "Error parsing API data.")

        if 'error' in response and response['error']:
            cardinal.sendMsg(channel, "Unable to evaluate '%s'." % question)
            return

        try:
            answer = response['answer']

            cardinal.sendMsg(channel, "%s = %s" % (str(question), str(answer)))
        except IndexError:
            cardinal.sendMsg(channel, "An error occurred while processing the calculation.")

    calculate.commands = ['calc', 'c', 'calculate']
    calculate.help = ["Calculate using math.js API.",
                      "Syntax: .calc <query>"]

def setup():
    return CalculatorPlugin()
