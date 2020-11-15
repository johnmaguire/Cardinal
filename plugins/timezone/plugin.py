from builtins import object
import logging
from datetime import datetime

import pytz
from pytz.exceptions import UnknownTimeZoneError

from cardinal.decorators import command, help

TIME_FORMAT = '%b %d, %I:%M:%S %p UTC%z'


class TimezonePlugin(object):
    @command(['time'])
    @help("Returns the current time in a given time zone or GMT offset.")
    @help("Syntax: time <GMT offset or timezone>")
    def get_time(self, cardinal, user, channel, msg):
        utc = pytz.utc
        now = datetime.now(utc)

        try:
            tz_input = msg.split(' ', 1)[1].strip()
        except IndexError:
            # no timezone specified, default to UTC
            return cardinal.sendMsg(channel, now.strftime(fmt))

        # handle common offset formats
        if (tz_input.startswith('UTC') or tz_input.startswith('GMT')) and \
                len(tz_input) > 3 and tz_input[3] in ('+', '-'):
            tz_input = tz_input[3:]

        offset = None
        try:
            offset = int(tz_input)
        except ValueError:
            pass

        if offset is not None:
            try:
                if offset < 0:
                    # for some reason the GMT+4 == America/Eastern, and GMT-4 is over in Asia
                    user_tz = pytz.timezone('Etc/GMT+{0}'.format(offset * -1))
                elif offset > 0:
                    user_tz = pytz.timezone('Etc/GMT{0}'.format(offset * -1))
                else:
                    user_tz = utc
            except UnknownTimeZoneError:
                return cardinal.sendMsg(channel, 'Invalid UTC offset')
        else:
            try:
                user_tz = pytz.timezone(tz_input)
            except UnknownTimeZoneError:
                return cardinal.sendMsg(channel, 'Invalid timezone')

        now = user_tz.normalize(now)
        cardinal.sendMsg(channel, now.strftime(TIME_FORMAT))

def setup():
    return TimezonePlugin()
