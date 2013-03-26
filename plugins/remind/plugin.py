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

from twisted.internet import reactor

class RemindPlugin(object):
    def remind(self, cardinal, user, channel, msg):
        message = msg.split(None, 2)
        if len(message) < 3:
            cardinal.sendMsg(channel, "Syntax: .remind <minutes> <message>")
            return
        
        try:
            reactor.callLater(60 * int(message[1]), cardinal.sendMsg, user.group(1), message[2])
            cardinal.sendMsg(channel, "%s: You will be reminded in %d minutes." % (user.group(1), int(message[1])))
        except ValueError:
            cardinal.sendMsg(channel, "You did not give a valid number of minutes to be reminded in.")
            
    remind.commands = ['remind']
    remind.help = ["Sets up a reminder, where the bot will message the user after a predetermined time.",
                   "Syntax: .remind <seconds> <message>"]

def setup():
    return RemindPlugin()
