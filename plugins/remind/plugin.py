import threading

from cardinal.decorators import command, help


class RemindPlugin(object):
    @command('remind')
    @help("Sends a reminder after a set time.")
    @help("Syntax: .remind <minutes> <message>")
    def remind(self, cardinal, user, channel, msg):
        message = msg.split(None, 2)
        if len(message) < 3:
            cardinal.sendMsg(channel, "Syntax: .remind <minutes> <message>")
            return

        timer = threading.Timer(60 * int(message[1]),
                                cardinal.sendMsg, (user.group(1), message[2]))
        timer.start()

        cardinal.sendMsg(channel,
                         "%s: You will be reminded in %d minutes." %
                         (user.group(1), int(message[1])))


def setup():
    return RemindPlugin()
