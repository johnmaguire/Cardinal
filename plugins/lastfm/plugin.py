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
        self._connect_or_create_db(cardinal)

    def _connect_or_create_db(self, cardinal):
        try:
            self.conn = sqlite3.connect(os.path.join(cardinal.path, 'db', 'lastfm-%s.db' % cardinal.network))
        except Exception, e:
            self.conn = None
            print >> sys.stderr, "ERROR: Unable to access local Last.fm database (%s)" % e
            return

        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (nick text collate nocase, vhost text, username text)")
        self.conn.commit()

    def set_user(self, cardinal, user, channel, msg):
        if not self.conn:
            cardinal.sendMsg(channel, "Unable to access local Last.fm database.")
            return

        message = msg.split()
        if len(message) < 2:
            cardinal.sendMsg(channel, "Syntax: .setlastfm <username>")
            return

        nick = user.group(1)
        vhost = user.group(3)
        username = message[1]

        c = self.conn.cursor()
        c.execute("SELECT username FROM users WHERE nick=? OR vhost=?", (nick, vhost))
        result = c.fetchone()
        if result:
            c.execute("UPDATE users SET username=? WHERE nick=? OR vhost=?", (username, nick, vhost))
        else:
            c.execute("INSERT INTO users (nick, vhost, username) VALUES(?, ?, ?)", (nick, vhost, username))
        self.conn.commit()

        cardinal.sendMsg(channel, "Your Last.fm username is now set to %s." % (username,))

    set_user.commands = ['setlastfm']
    set_user.help = ["Sets the default Last.fm username for your nick.",
                     "Syntax: .setlastfm <username>"]

    def now_playing(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query Last.fm
        if not hasattr(cardinal.config['lastfm'], 'API_KEY') or cardinal.config['lastfm'].API_KEY == "API_KEY":
            cardinal.sendMsg(channel, "Last.fm plugin is not configured correctly. Please set API key.")
            return

        if not self.conn:
            cardinal.sendMsg(channel, "Unable to access local Last.fm database.")
            return

        # Open the cursor for the query to find a saved Last.fm username
        c = self.conn.cursor()

        # If they supplied user parameter, use that for the query instead
        message = msg.split()
        
        if len(message) >= 2:
            nick = message[1]
            c.execute("SELECT username FROM users WHERE nick=?", (nick,))
        else:
            nick = user.group(1)
            vhost = user.group(3)
            c.execute("SELECT username FROM users WHERE nick=? OR vhost=?", (nick, vhost))
        result = c.fetchone()

        # Use the returned username, or the entered/user's nick otherwise
        if not result:
            try:
                username = message[1]
            except IndexError:
                username = user.group(1)
        else:
            username = result[0]

        try:
            uh = urllib2.urlopen("http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=%s&limit=1&format=json" % (username, cardinal.config['lastfm'].API_KEY))
            content = json.load(uh)
        except urllib2.URLError, e:
            cardinal.sendMsg(channel, "Unable to reach Last.fm.")
            print >> sys.stderr, "ERROR: Failed to reach the server: %s" % e.reason
            return
        except urllib2.HTTPError, e:
            cardinal.sendMsg(channel, "Unable to access Last.fm API.")
            print >> sys.stderr, "ERROR: The server did not fulfill the request. (%s Error)" % e.code
            return

        if 'error' in content and content['error'] == 10:
            cardinal.sendMsg(channel, "Last.fm plugin is not configured correctly. Please set API key.")
            return
        elif 'error' in content and content['error'] == 6:
            cardinal.sendMsg(channel, "Your Last.fm username is incorrect. No user exists by the username %s." % str(username))
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
                cardinal.sendMsg(channel, "Unable to find any tracks played. (Is your Last.fm username correct?)")

    now_playing.commands = ['np', 'nowplaying']
    now_playing.help = ["Get the Last.fm track currently played by a user (attempts to default to username set with .setlastfm)",
                        "Syntax: .np [username]"]

    def compare(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query Last.fm
        if not hasattr(cardinal.config['lastfm'], 'API_KEY') or cardinal.config['lastfm'].API_KEY == "API_KEY":
            cardinal.sendMsg(channel, "Last.fm plugin is not configured correctly. Please set API key.")

        if not self.conn:
            cardinal.sendMsg(channel, "Unable to access local Last.fm database.")
            return

        # Open the cursor for the query to find a saved Last.fm username
        c = self.conn.cursor()

        # If they supplied user parameter, use that for the query instead
        message = msg.split()
        if len(message) < 2:
            cardinal.sendMsg(channel, "Syntax: .compare <username> [username]")

        nick = message[1]
        c.execute("SELECT username FROM users WHERE nick=?", (nick,))
        result = c.fetchone()

        if not result:
            username1 = nick
        else:
            username1 = result[0]

        if len(message) >= 3:
            nick = message[2]
            c.execute("SELECT username FROM users WHERE nick=?", (nick,))
        else:
            nick = user.group(1)
            vhost = user.group(3)
            c.execute("SELECT username FROM users WHERE nick=? OR vhost=?", (nick, vhost))
        result = c.fetchone()

        # Use the returned username, or the entered/user's nick otherwise
        if not result:
            username2 = nick
        else:
            username2 = result[0]

        try:
            uh = urllib2.urlopen("http://ws.audioscrobbler.com/2.0/?method=tasteometer.compare&type1=user&type2=user&value1=%s&value2=%s&api_key=%s&format=json" % (username1, username2, cardinal.config['lastfm'].API_KEY))
            content = json.load(uh)
        except urllib2.URLError, e:
            cardinal.sendMsg(channel, "Unable to reach Last.fm.")
            print >> sys.stderr, "ERROR: Failed to reach the server: %s" % e.reason
            return
        except urllib2.HTTPError, e:
            cardinal.sendMsg(channel, "Unable to access Last.fm API.")
            print >> sys.stderr, "ERROR: The server did not fulfill the request. (%s Error)" % e.code
            return

        if 'error' in content and content['error'] == 10:
            cardinal.sendMsg(channel, "Last.fm plugin is not configured correctly. Please set API key.")
            return
        elif 'error' in content and content['error'] == 7:
            print content
            cardinal.sendMsg(channel, "One of the Last.fm usernames entered was invalid. Please try again.")
            return

        try:
            score = int(float(content['comparison']['result']['score']) * 100)
            artists = []
            if not 'artist' in content['comparison']['result']['artists']:
                # Return early to avoid error on looping through artists
                cardinal.sendMsg(channel, "According to Last.fm's Tasteometer, %s and %s share none of the same music." % (str(username1), str(username2)))
                return
            
            # Account for Last.fm giving a string instead of a list if only one artist is shared
            if not isinstance(content['comparison']['result']['artists']['artist'], list):
                artists.append(str(content['comparison']['result']['artists']['artist']['name']))
            else:
                # Loop through all artists to grab artist names
                for i in range(len(content['comparison']['result']['artists']['artist'])):
                    artists.append(str(content['comparison']['result']['artists']['artist'][i]['name']))

            cardinal.sendMsg(channel, "According to Last.fm's Tasteometer, %s and %s's music preferences are %d%% compatible! Some artists they have in common include: %s" % (str(username1), str(username2), score, ', '.join(artists)))
        except KeyError:
            cardinal.sendMsg(channel, "An unknown error has occurred.")

    compare.commands = ['compare']
    compare.help = ["Uses Last.fm to compare the compatibility of music between two users.",
                    "Syntax: .compare <username> [username]"]

    def close(self):
        self.conn.close()

def setup(cardinal):
    return LastfmPlugin(cardinal)
