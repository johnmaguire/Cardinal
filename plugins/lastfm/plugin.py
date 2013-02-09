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

import os
import sys
import sqlite3
import json
import urllib2

class LastfmPlugin(object):
    # This will hold the connection to the sqlite database
    conn = None

    def __init__(self, cardinal):
        # Connect to or create the database
        self.connect_or_create_db(cardinal)

    def connect_or_create_db(self, cardinal):
        try:
            self.conn = sqlite3.connect(os.path.join(cardinal.path, 'db', 'lastfm.db'))
        except Exception, e:
            self.conn = None
            print >> sys.stderr, "ERROR: Unable to access local Last.fm database (%s)" % e
            return

        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (nick text, vhost text, username text)")
        self.conn.commit()

    def set_user(self, cardinal, user, channel, msg):
        if not self.conn:
            cardinal.sendMsg(channel, "Unable to access local Last.fm database.")

        split_msg = msg.split()
        if len(split_msg) < 2:
            return

        c = self.conn.cursor()
        c.execute("SELECT username FROM users WHERE nick=? OR vhost=?", (user.group(1), user.group(3)))
        result = c.fetchone()
        if result:
            c.execute("UPDATE users SET username=? WHERE nick=? OR vhost=?", (split_msg[1], user.group(1), user.group(3)))
        else:
            c.execute("INSERT INTO users (nick, vhost, username) VALUES(?, ?, ?)", (user.group(1), user.group(3), split_msg[1]))
        self.conn.commit()

        cardinal.sendMsg(channel, "Your Last.fm username is now set to %s." % (split_msg[1]))

    set_user.commands = ['setlastfm']

    def now_playing(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query Last.fm
        if not hasattr(cardinal.config['lastfm'], 'API_KEY') or cardinal.config['lastfm'].API_KEY == "API_KEY":
            cardinal.sendMsg(channel, "Plugin is not configured correctly. Please set API key.")

        if not self.conn:
            cardinal.sendMsg(channel, "Unable to access local Last.fm database.")
            return

        c = self.conn.cursor()
        c.execute("SELECT username FROM users WHERE nick=? OR vhost=?", (user.group(1), user.group(3)))
        result = c.fetchone()
        if not result:
            cardinal.sendMsg(channel, "Username not set. Use .setlastfm <user> to set your username.")
            return
        
        username = result[0]

        uh = urllib2.urlopen("http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=%s&limit=1&format=json" % (username, cardinal.config['lastfm'].API_KEY))
        content = json.load(uh)

        if 'error' in content and content['error'] == 10:
            cardinal.sendMsg(channel, "Plugin is not configured correctly. Please set API key.")
            return
        elif 'error' in content and content['error'] == 6:
            cardinal.sendMsg(channel, "Your username is incorrect. No user exists by the username %s." % str(username))
            return

        try:
            song = content['recenttracks']['track'][0]['name']
            artist = content['recenttracks']['track'][0]['artist']['#text']

            cardinal.sendMsg(channel, "%s is now listening to: %s by %s" % (str(username), str(song), str(artist)))
        except KeyError:
            try:
                song = content['recenttracks']['track']['name']
                artist = content['recenttracks']['track']['artist']['#text']

                cardinal.sendMsg(channel, "%s last listened to: %s by %s" % (str(username), str(song), str(artist)))
            except KeyError:
                cardinal.sendMsg(channel, "Unable to find any tracks played. (Is your username correct?)")

    now_playing.commands = ['np', 'nowplaying']

    def __del__(self):
        self.conn.close()

def setup(cardinal):
    return LastfmPlugin(cardinal)
