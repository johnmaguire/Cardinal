# Copyright (c) 2013 John Maguire <john@leftforliving.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation the 
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or 
# sell copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS 
# IN THE SOFTWARE.

import sqlite3
import json
import urllib2

from plugins.lastfm import config

class LastfmPlugin(object):
    # This will hold the connection to the sqlite database
    conn = None

    def __init__(self):
        try:
            self.conn = sqlite3.connect('users.db')
        except:
            return

        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (nick text, vhost text, username text)")
        self.conn.commit()

    def set_user(self, cardinal, user, channel, msg):
        split_msg = msg.split()
        if len(split_msg) < 2:
            return

        c = self.conn.cursor()
        c.execute("SELECT username FROM users WHERE nick=? OR vhost=?", (user.group(1), user.group(3)))
        result = c.fetchone()
        if result:
            print "Updating database."
            c.execute("UPDATE users SET username=? WHERE nick=? OR vhost=?", (split_msg[1], user.group(1), user.group(3)))
        else:
            print "Inserting into database."
            c.execute("INSERT INTO users (nick, vhost, username) VALUES(?, ?, ?)", (user.group(1), user.group(3), split_msg[1]))
        self.conn.commit()

        cardinal.sendMsg(channel, "New Last.fm username is %s" % (split_msg[1]))
    set_user.commands = ['setlastfm']

    def now_playing(self, cardinal, user, channel, msg):
        c = self.conn.cursor()
        c.execute("SELECT username FROM users WHERE nick=? OR vhost=?", (user.group(1), user.group(3)))
        result = c.fetchone()
        if not result:
            cardinal.sendMsg(channel, "Username not set. Use .setlastfm <user> to set your username.")
        
        username = result[0]

        uh = urllib2.urlopen("http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=%s&limit=1&format=json" % (username, config.API_KEY))
        content = json.load(uh)
        try:
            song = content['recenttracks']['track'][0]['name']
            artist = content['recenttracks']['track'][0]['artist']['#text']

            message = "%s is now listening to: %s by %s" % (str(username), str(song), str(artist))
        except KeyError:
            try:
                song = content['recenttracks']['track']['name']
                artist = content['recenttracks']['track']['artist']['#text']

                message = "%s last listened to: %s by %s" % (str(username), str(song), str(artist))
            except KeyError:
                message = "Either the username is incorrect or no tracks have been played."

        cardinal.sendMsg(channel, message)

    now_playing.commands = ['np', 'nowplaying']

def setup():
    instance = LastfmPlugin()

    return [
        instance.set_user,
        instance.now_playing,
    ]
