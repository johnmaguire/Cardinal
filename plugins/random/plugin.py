import random
import re

from cardinal.decorators import command, help

# Maximum number of dice we will roll at one time
DICE_LIMIT = 10


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

    # Ignore 1-sided dice, or large dice
    if sides < 2 or sides > 120:
        return []

    # Don't let people exhaust memory
    if num_dice > 10:
        num_dice = 10

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
            if len(dice) >= DICE_LIMIT:
                break

        dice = dice[:DICE_LIMIT]

        # Ignore things like 2d0, 0d2, etc.
        if not dice:
            return

        results = []
        sum_ = 0
        for sides in dice:
            roll = random.randint(1, sides)

            results.append((sides, roll))
            sum_ += roll

        count = len(dice)
        messages = '  '.join(
            ["Rolling {} {}...".format(count, "die" if count < 2 else "dice")]
            + [f"d{sides}:{result}" for sides, result in results]
            + [f"Total: {sum_}"]
        )

        cardinal.sendMsg(channel, messages)


entrypoint = RandomPlugin
