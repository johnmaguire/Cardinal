from builtins import object
from cardinal.decorators import command, help, regex


class PingPlugin(object):
    @regex(r'(?i)^ping[.?!]?$')
    @command(['ping'])
    @help("Responds to a ping message with 'Pong.'")
    def pong(self, cardinal, user, channel, msg):
        if channel != user:
            cardinal.sendMsg(channel, "%s: Pong." % user.nick)
        else:
            cardinal.sendMsg(channel, "Pong.")

def setup():
    return PingPlugin()
