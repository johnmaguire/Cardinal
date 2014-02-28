class PingPlugin(object):
    def pong(self, cardinal, user, channel, msg):
        if channel != user:
            cardinal.sendMsg(channel, "%s: Pong." % user.group(1))
        else:
            cardinal.sendMsg(channel, "Pong.")

    pong.regex = r'(?i)^ping[.?!]?$'
    pong.commands = ['ping']
    pong.help = "Responds to a ping message with 'Pong.'"

def setup():
    return PingPlugin()
