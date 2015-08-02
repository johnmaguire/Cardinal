import logging
from pytz import timezone
from datetime import datetime
import pytz
from pytz.exceptions import UnknownTimeZoneError

class TimezonePlugin(object):
    def get_time(self, cardinal, user, channel, msg):
        #
        utc = pytz.utc
        utc_dt = utc.localize(datetime.now()).replace(tzinfo=utc)
        fmt = '%m/%d %H:%M'
        
        try:
            time_zone_input = msg.split(' ', 1)[1]
        except IndexError:
            cardinal.sendMsg(channel, utc_dt.strftime(fmt))# user didn't specify a time, return GMT
            return
        
        try:
            offset = int(time_zone_input)
        except ValueError:
            offset = None
            time_zone_input = time_zone_input.strip()
        
        if not offset is None:
            try:
                if offset < 0:
                    user_tz = timezone('Etc/GMT+{0}'.format(offset * -1))#for some reason the GMT+4 == America/Eastern, and GMT-4 is over in Asia
                elif offset > 0:
                    user_tz = timezone('Etc/GMT{0}'.format(offset * -1))
                else:
                    user_tz = utc
            except UnknownTimeZoneError:
                cardinal.sendMsg(channel, 'Invalid GMT offset')
                return
        else:
            try:
                user_tz = timezone(time_zone_input)
            except UnknownTimeZoneError:
                cardinal.sendMsg(channel, 'Invalid Timezone')
                return
                
        user_dt = user_tz.normalize(utc_dt.astimezone(user_tz))
        cardinal.sendMsg(channel, user_dt.strftime(fmt))
        
    get_time.commands = ['time']
    get_time.help = ['Returns the current time in a given time zone or GMT offset. Syntax: time <GMT offset or timzone>']

def setup():
    return TimezonePlugin()