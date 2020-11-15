from builtins import object
from twisted.internet import error, reactor

from cardinal.decorators import command, help


class RemindPlugin(object):
    def __init__(self):
        self.call_ids = []

    @command('remind')
    @help("Sends a reminder after a set time.")
    @help("Syntax: .remind <minutes> <message>")
    def remind(self, cardinal, user, channel, msg):
        message = msg.split(None, 2)
        if len(message) < 3:
            cardinal.sendMsg(channel, "Syntax: .remind <minutes> <message>")
            return

        self.call_ids.append(reactor.callLater(60 * int(message[1]),
                                cardinal.sendMsg, user.nick, message[2]))

        cardinal.sendMsg(channel,
                         "%s: You will be reminded in %d minutes." %
                         (user.nick, int(message[1])))

    def close(self):
        for call_id in call_ids:
            try:
                call_id.cancel()
            except error.AlreadyCancelled:
                pass


def setup():
    return RemindPlugin()
