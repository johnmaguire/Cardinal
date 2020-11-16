from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import os
import sqlite3
import json
import urllib.request, urllib.error, urllib.parse
import logging

from cardinal.decorators import command, help


class LastfmPlugin(object):
    def __init__(self, cardinal, config):
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Connect to or create the database
        self._connect_or_create_db(cardinal)

        self.config = config or {}
        self.config.setdefault('api_key', None)

    @property
    def api_key(self):
        return self.config['api_key']

    def _connect_or_create_db(self, cardinal):
        self.conn = None
        try:
            self.conn = sqlite3.connect(os.path.join(
                cardinal.storage_path,
                'database',
                'lastfm-%s.db' % cardinal.network
            ))
        except Exception:
            self.logger.exception("Unable to access local Last.fm database")
            return

        c = self.conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "   nick text collate nocase,"
            "   vhost text,"
            "   username text"
            ")"
        )
        self.conn.commit()


    @command('setlastfm')
    @help(["Sets the default Last.fm username for your nick.",
           "Syntax: .setlastfm <username>"])
    def set_user(self, cardinal, user, channel, msg):
        if not self.conn:
            cardinal.sendMsg(
                channel,
                "Unable to access local Last.fm database."
            )
            self.logger.error(
                "Attempt to set username failed, no database connection"
            )
            return

        message = msg.split()
        # If using natural syntax, remove Cardinal's name
        if message[0] != '.setlastfm':
            message.pop(0)

        if len(message) < 2:
            cardinal.sendMsg(channel, "Syntax: .setlastfm <username>")
            return

        nick = user.nick
        vhost = user.vhost
        username = message[1]

        c = self.conn.cursor()
        c.execute(
            "SELECT username FROM users WHERE nick=? OR vhost=?",
            (nick, vhost)
        )
        result = c.fetchone()
        if result:
            c.execute(
                "UPDATE users SET username=? WHERE nick=? OR vhost=?",
                (username, nick, vhost)
            )
        else:
            c.execute(
                "INSERT INTO users (nick, vhost, username) VALUES(?, ?, ?)",
                (nick, vhost, username)
            )
        self.conn.commit()

        cardinal.sendMsg(
            channel,
            "Your Last.fm username is now set to %s." % username
        )


    @command(['np', 'nowplaying'])
    @help("Get the Last.fm track currently played by a user (defaults to "
           "username set with .setlastfm)")
    @help("Syntax: .np [username]")
    def now_playing(self, cardinal, user, channel, msg):
        # Before we do anything, let's make sure we'll be able to query Last.fm
        if self.api_key is None:
            cardinal.sendMsg(
                channel,
                "Last.fm plugin is not configured. Please set API key."
            )
            self.logger.error(
                "Attempt to get now playing failed, API key not set"
            )
            return

        if not self.conn:
            cardinal.sendMsg(
                channel,
                "Unable to access local Last.fm database."
            )
            self.logger.error(
                "Attempt to get now playing failed, no database connection"
            )
            return

        # Open the cursor for the query to find a saved Last.fm username
        c = self.conn.cursor()

        message = msg.split()

        # If using natural syntax, remove Cardinal's name
        if message[0] != '.np' and message[0] != '.nowplaying':
            message.pop(0)

        # If they supplied user parameter, use that for the query instead
        if len(message) >= 2:
            nick = message[1]
            c.execute("SELECT username FROM users WHERE nick=?", (nick,))
        else:
            nick = user.nick
            vhost = user.vhost
            c.execute(
                "SELECT username FROM users WHERE nick=? OR vhost=?",
                (nick, vhost)
            )
        result = c.fetchone()

        # Use the returned username, or the entered/user's nick otherwise
        if not result:
            try:
                username = message[1]
            except IndexError:
                username = user.nick
        else:
            username = result[0]

        try:
            uh = urllib.request.urlopen(
                "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks"
                "&user=%s&api_key=%s&limit=1&format=json" %
                (username, self.api_key)
            )
            content = json.load(uh)
        except Exception as e:
            # Handle 404 (i.e. user not exists) separately
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                cardinal.sendMsg(
                        channel,
                        "Last.fm user '{}' does not exist".format(username))
                return

            cardinal.sendMsg(channel, "Unable to connect to Last.fm.")
            self.logger.exception("Failed to connect to Last.fm")
            return

        if 'error' in content and content['error'] == 10:
            cardinal.sendMsg(
                channel,
                "Last.fm plugin is not configured. Please set API key."
            )
            self.logger.error(
                "Attempt to get now playing failed, API key incorrect"
            )
            return
        elif 'error' in content and content['error'] == 6:
            cardinal.sendMsg(
                channel,
                "Your Last.fm username is incorrect. No user exists by the "
                "username %s." % str(username)
            )
            return

        try:
            song = content['recenttracks']['track'][0]['name']
            artist = content['recenttracks']['track'][0]['artist']['#text']

            cardinal.sendMsg(
                channel,
                "%s is now listening to: %s by %s" %
                (str(username), str(song), str(artist))
            )
        except IndexError:
            cardinal.sendMsg(
                channel,
                "Last.fm user '{}' hasn't listened to anything yet".format(
                    username))

    def close(self):
        if self.conn:
            self.conn.close()


def setup(cardinal, config):
    return LastfmPlugin(cardinal, config)
