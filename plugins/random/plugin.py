import random

from cardinal.decorators import command


class RandomPlugin:
    @command('roll')
    def roll(self, cardinal, user, channel, msg):
        args = msg.split(' ')
        args.pop(0)

        dice = []
        for arg in args:
            try:
                sides = int(arg)
                dice.append(sides)
            except (TypeError, ValueError):
                if arg[0] != 'd':
                    continue

                try:
                    sides = int(arg[1:])
                    dice.append(sides)
                except (TypeError, ValueError):
                    pass

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
