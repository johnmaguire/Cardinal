import random
import re

from cardinal.decorators import command, help


def parse_roll(arg):
    # some people might separate with commas
    arg = arg.rstrip(',')

    if match := re.match(r'^(\d+)?d(\d+)$', arg):
        num_dice = match.group(1)
        sides = match.group(2)
    elif match := re.match(r'^d?(\d+)$', arg):
        num_dice = 1
        sides = match.group(1)
    else:
        return []

    return [int(sides)] * int(num_dice)


class RandomPlugin:
    @command('roll')
    @help("Roll dice")
    @help("Syntax: .roll #d# (e.g. .roll 2d6)")
    def roll(self, cardinal, user, channel, msg):
        args = msg.split(' ')
        args.pop(0)
        if not args:
            return

        dice = []
        for arg in args:
            dice = dice + parse_roll(arg)

        results = []
        limit = 10
        for sides in dice:
            if sides < 2 or sides > 120:
                continue

            limit -= 1
            # Don't allow more than ten dice rolled at a time
            if limit < 0:
                break

            results.append((sides, random.randint(1, sides)))

        messages = ', '.join(
            [f"d{sides}: {result}" for sides, result in results]
        )

        cardinal.sendMsg(channel, messages)


entrypoint = RandomPlugin
