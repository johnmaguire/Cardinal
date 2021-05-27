import os
import sqlite3
import logging

import requests
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from cardinal.decorators import command, help


class LastfmPlugin:
    def __init__(self, cardinal, config):
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        self.cardinal = cardinal

        self.config = config or {}
        if 'api_key' not in self.config:
            raise Exception("Missing required api_key in config")

        # Connect to or create the database - raises on failure
        self._connect_or_create_db(cardinal)

    @property
    def api_key(self):
        return self.config['api_key']

    def _connect_or_create_db(self, cardinal):
        self.conn = None
        self.conn = sqlite3.connect(os.path.join(
            cardinal.storage_path,
            'database',
            'lastfm-%s.db' % cardinal.network
        ))

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
        if len(message) != 2:
            cardinal.sendMsg(channel, "Syntax: .setlastfm <username>")
            return

        nick = user.nick
        vhost = user.vhost
        username = message[1]

        try:
            self._get_or_update_username(nick, vhost, username)
        except Exception:
            self.logger.exception("Error updating Last.fm username")
            cardinal.sendMsg(channel, "An unknown error occurred.")
            return

        cardinal.sendMsg(
            channel,
            "Your Last.fm username is now set to %s." % username
        )

    def _get_or_update_username(self, nick, vhost, username):
        # Check if a user already exists
        c = self.conn.cursor()
        c.execute(
            "SELECT username FROM users WHERE nick=? OR vhost=?",
            (nick, vhost)
        )
        result = c.fetchone()

        # Update or insert
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

    @command(['np', 'nowplaying'])
    @help("Get the Last.fm track currently played by a user (defaults to "
          "username set with .setlastfm)")
    @help("Syntax: .np [Last.fm username]")
    @defer.inlineCallbacks
    def now_playing(self, cardinal, user, channel, msg):
        # Open the cursor for the query to find a saved Last.fm username
        c = self.conn.cursor()

        message = msg.split()
        if len(message) > 2:
            cardinal.sendMsg(channel, "Syntax: .np [Last.fm username]")
            return

        # If they supplied user parameter, use that for the query instead
        if len(message) == 2:
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
        try:
            username = message[1]
        except IndexError:
            username = user.nick

        if result:
            username = result[0]

        try:
            msg = yield self._get_np_result(username)
        except Exception:
            self.logger.exception("Error communicating with Last.fm")
            cardinal.sendMsg(channel, "Error communicating with Last.fm")
            return

        cardinal.sendMsg(channel, msg)

    @defer.inlineCallbacks
    def _get_np_result(self, username):
        r = yield deferToThread(
            requests.get,
            "http://ws.audioscrobbler.com/2.0/",
            params={
                "method": "user.getrecenttracks",
                "user": username,
                "api_key": self.api_key,
                "limit": 1,
                "format": "json",
            }
        )

        if r.status_code == 404:
            return "Last.fm user '{}' does not exist".format(username)
        # any other error code is unexpected
        r.raise_for_status()

        # check for known errors
        content = r.json()
        if 'error' in content and content['error'] == 10:
            self.logger.error(
                "Attempt to get now playing failed, API key incorrect"
            )
            return "Last.fm plugin is not configured. Please set API key."
        elif 'error' in content and content['error'] == 6:
            return (
                "Your Last.fm username is incorrect. No user exists by the "
                "username %s." % str(username))
        elif 'error' in content:
            self.logger.error("Unknown error in API response: {}".format(
                content['error']
            ))
            return "Unknown error while communicating with Last.fm"

        # finally, give successful result
        try:
            song = content['recenttracks']['track'][0]['name']
            artist = content['recenttracks']['track'][0]['artist']['#text']
        except IndexError:
            return "Last.fm user '{}' hasn't listened to anything yet".format(
                    username)

        msg = "%s is now listening to: %s by %s" % (
            str(username), str(song), str(artist))

        yt_url = yield self._get_yt_url(song, artist)
        if yt_url is not None:
            msg = msg + " - YouTube: {}".format(yt_url)

        return msg

    @defer.inlineCallbacks
    def _get_yt_url(self, song, artist):
        # XXX does this look safe to you?
        try:
            yt = self.cardinal.plugin_manager.plugins['youtube']['instance']
        except KeyError:
            return None

        video = yield yt._search("{} {}".format(song, artist))
        if video is None:
            return

        return "https://youtu.be/watch?v={}".format(video['id']['videoId'])

    def close(self):
        if self.conn:
            self.conn.close()


entrypoint = LastfmPlugin
