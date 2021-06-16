import random
import re

from cardinal.decorators import command, help


def parse_roll(arg):
    # some people might separate with commas
    arg = arg.rstrip(',')

    # regex intentionally does not match negatives
    if match := re.match(r'^(\d+)d(\d+)$', arg):
        num_dice = int(match.group(1))
        sides = int(match.group(2))
    elif match := re.match(r'^d?(\d+)$', arg):
        num_dice = 1
        sides = int(match.group(1))
    else:
        return []

    # Ignore things like 2d0, 0d2, etc.
    if num_dice == 0 or sides == 0:
        return []

    return [sides] * num_dice


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

        # Ignore things like 2d0, 0d2, etc.
        if not dice:
            return

        results = []
        limit = 10
        sum_ = 0
        for sides in dice:
            if sides < 2 or sides > 120:
                continue

            limit -= 1
            # Don't allow more than ten dice rolled at a time
            if limit < 0:
                break

            roll = random.randint(1, sides)
            results.append((sides, roll))
            sum_ += roll

        messages = '  '.join(
            [f"d{sides}:{result}" for sides, result in results] +
            [f"Total: {sum_}"]
        )

        cardinal.sendMsg(channel, messages)


entrypoint = RandomPlugin
