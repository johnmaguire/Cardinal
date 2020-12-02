import random

from twisted.internet import defer

from cardinal.decorators import command, help
from cardinal.util import sleep


class Magic8Ball(object):
    @command(['8', '8ball'])
    @help("Ask the might 8-ball a question.")
    @help("Syntax: .8 <question>")
    @defer.inlineCallbacks
    def answer(self, cardinal, user, channel, msg):
        if not (msg.endswith("?") and len(msg.split()) > 1):
            cardinal.sendMsg(channel, "Was that a question?")
            return

        cardinal.sendMsg(
            channel,
            "Let me dig deep into the waters of life, and find your answer."
        )
        yield sleep(2)
        cardinal.sendMsg(channel, "Hmmm...")
        yield sleep(2)
        cardinal.sendMsg(channel, self._get_random_answer())

    def _get_random_answer(self):
        answers = ['It is certain', 'It is decidedly so', 'Without a doubt',
                   'Yes definitely', 'You may rely on it', 'As I see it, yes',
                   'Most likely', 'Outlook good', 'Yes', 'Signs point to yes',
                   'Reply hazy try again', 'Ask again later',
                   'Better not tell you now', 'Cannot predict now',
                   'Concentrate and ask again', "Don't count on it",
                   'My reply is no', 'My sources say no',
                   'Outlook not so good', 'Very doubtful']

        return random.choice(answers)


def setup():
    return Magic8Ball()
