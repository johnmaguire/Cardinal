import random, time, threading

class Magic8Ball(object):
    def answer(self, cardinal, user, channel, msg):
        if msg.endswith("?") and len(msg.split()) > 1:
            cardinal.sendMsg(channel, "Let me dig deep into the waters of life, and find your answer.")
            threading.Timer(2, cardinal.sendMsg, (channel, "Hmmm...")).start()
            threading.Timer(4, cardinal.sendMsg, (channel, self._get_random_answer())).start()
        else:
            cardinal.sendMsg(channel, "Was that a question?")

    answer.commands = ["8", "8ball"]
    answer.help = ["Ask the mighy 8-Ball a question.",
                   "Syntax: .8 <question>"]

    def _get_random_answer(self):
        answers = ['It is certain', 'It is decidedly so', 'Without a doubt',
                   'Yes definitely', 'You may rely on it', 'As I see it, yes',
                   'Most likely', 'Outlook good', 'Yes', 'Signs point to yes',
                   'Reply hazy try again', 'Ask again later',
                   'Better not tell you now', 'Cannot predict now', 'Concentrate and ask again',
                   "Don't count on it", 'My reply is no', 'My sources say no',
                   'Outlook not so good', 'Very doubtful']

        return random.choice(answers)

def setup():
    return Magic8Ball()
