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
        except AssertionError:
            cardinal.sendMsg(channel, "You did not give a valid number of minutes to be reminded in.")

    remind.commands = ['remind']
    remind.help = ["Sets up a reminder, where the bot will message the user after a predetermined time.",
                   "Syntax: .remind <minutes> <message>"]

def setup():
    return RemindPlugin()
