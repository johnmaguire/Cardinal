

import signal
import json
import logging
import os
import re
from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime

from twisted.internet import defer, protocol, reactor
from twisted.internet.task import deferLater
from twisted.words.protocols import irc

from cardinal.plugins import PluginManager, EventManager
from cardinal.exceptions import (
    CommandNotFoundError,
    ConfigNotFoundError,
    LockInUseError,
    PluginError,
)

USER_REGEX = re.compile(r'^(.*?)!(.*?)@(.*?)$')

user_info = namedtuple('user_info', ('nick', 'user', 'vhost'))

# Database locking constants
UNLOCKED = 'unlocked'
LOCKED = 'locked'


class CardinalBot(irc.IRCClient, object):
    """Cardinal, in all its glory"""

    @property
    def network(self):
        return self.factory.network

    @network.setter
    def network(self, value):
        self.factory.network = value

    @property
    def nickname(self):
        return self.factory.nickname

    @nickname.setter
    def nickname(self, value):
        self.factory.nickname = value

    @property
    def password(self):
        """Twisted.irc.IRCClient server password setting"""
        return self.factory.server_password

    @password.setter
    def password(self, value):
        self.factory.server_password = value

    @property
    def username(self):
        return self.factory.username

    @username.setter
    def username(self, value):
        self.factory.username = value

    @property
    def realname(self):
        return self.factory.realname

    @realname.setter
    def realname(self, value):
        self.factory.realname = value

    @property
    def storage_path(self):
        return self.factory.storage_path

    def __init__(self):
        """Initializes the logging"""
        self.logger = logging.getLogger(__name__)
        self.irc_logger = logging.getLogger("%s.irc" % __name__)

        # Will get set by Twisted before signedOn is called
        self.factory = None

        # PluginManager gets created in signedOn
        self.plugin_manager = None

        # Setup EventManager
        self.event_manager = EventManager(self)

        # Register events
        self.event_manager.register("irc.raw", 2)
        self.event_manager.register("irc.invite", 2)
        self.event_manager.register("irc.privmsg", 3)
        self.event_manager.register("irc.notice", 3)
        self.event_manager.register("irc.nick", 2)
        self.event_manager.register("irc.mode", 3)
        self.event_manager.register("irc.topic", 3)
        self.event_manager.register("irc.join", 2)
        self.event_manager.register("irc.part", 3)
        self.event_manager.register("irc.kick", 4)
        self.event_manager.register("irc.quit", 2)

        # State variables for the WHO command
        self._who_cache = {}
        self._who_deferreds = {}

        # Database file locks
        self.db_locks = {}

    def signedOn(self):
        """Called once we've connected to a network"""
        super().signedOn()

        self.logger.info("Signed on as %s" % self.nickname)

        # Give the factory the instance it created in case it needs to
        # interface for error handling or metadata retention.
        self.factory.cardinal = self

        # Setup PluginManager
        self.plugin_manager = PluginManager(self,
                                            self.factory.plugins,
                                            self.factory.blacklist)

        if self.factory.server_commands:
            self.logger.info("Sending server commands")
            for command in self.factory.server_commands:
                self.send(command)

        # Attempt to identify with NickServ, if a password was given
        if self.factory.password:
            self.logger.info("Attempting to identify with NickServ")
            self.msg("NickServ", "IDENTIFY %s" % (self.factory.password,))

        # For servers that support it, set the bot mode
        self.send("MODE {} +B".format(self.nickname))

        # Attempt to join channels
        for channel in self.factory.channels:
            self.join(channel)

        # Set the uptime as now and grab the  boot time from the factory
        self.uptime = datetime.now()
        self.booted = self.factory.booted

    def joined(self, channel):
        """Called when we join a channel.

        channel -- Channel joined. Provided by Twisted.
        """
        self.logger.info("Joined %s" % channel)

    def lineReceived(self, line):
        """Called for every line received from the server."""
        # The IRC spec does not specify a message encoding, meaning that some
        # messages may fail to decode into a UTF-8 string. While we must be
        # aware of the issue and choose to replace "invalid" characters (which
        # are technically valid per the IRC RFC, hence us warning about this
        # behavior), we must also ensure that the Twisted IRCClient's
        # implementation of lineReceived does not receive these characters, as
        # it will not replace them.
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            self.logger.warning(
                    "Stripping non-UTF-8 data from received line: {}"
                    .format(line))
            line = line.decode('utf-8', 'replace')

        self.irc_logger.info(line)

        parts = line.split(' ')
        command = parts[1]

        self.event_manager.fire("irc.raw", command, line)

        # Send IRCClient the version of the line that has had non-UTF-8
        # characters replaced.
        #
        # Bug: https://twistedmatrix.com/trac/ticket/9443
        super().lineReceived(line.encode('utf-8'))

    def irc_PRIVMSG(self, prefix, params):
        """Called when we receive a message in a channel or PM."""
        super().irc_PRIVMSG(prefix, params)

        # Break down the user into usable groups
        user = self.get_user_tuple(prefix)
        nick = user[0]
        channel = params[0]
        message = params[1]

        self.logger.debug(
            "%s!%s@%s to %s: %s" %
            (user + (channel, message))
        )

        self.event_manager.fire("irc.privmsg", user, channel, message)

        # If the channel is ourselves, this is actually a PM to us, and so
        # we'll update the channel variable to the sender's username to make
        # replying a little easier.
        if channel == self.nickname:
            channel = nick

        # Attempt to call a command. If it doesn't appear to PluginManager to
        # be a command, this will just fall through. If it matches command
        # syntax but there is no matching command, then we should catch the
        # exception.
        try:
            self.plugin_manager.call_command(user, channel, message)
        except CommandNotFoundError:
            # This is just an info, since anyone can trigger it, not really a
            # bad thing.
            self.logger.info(
                "Unable to find a matching command", exc_info=True)

    def irc_NOTICE(self, prefix, params):
        """Called when a notice is sent to a channel or privately"""
        super().irc_NOTICE(prefix, params)

        user = self.get_user_tuple(prefix)
        channel = params[0]
        message = params[1]

        # Sent by network, not a real user
        if not user:
            self.logger.debug(
                "%s sent notice to %s: %s" % (prefix, channel, message)
            )
            return

        self.logger.debug(
            "%s!%s@%s sent notice to %s: %s" %
            (user + (channel, message))
        )

        self.event_manager.fire("irc.notice", user, channel, message)

    def irc_NICK(self, prefix, params):
        """Called when a user changes their nick"""
        super().irc_NICK(prefix, params)

        user = self.get_user_tuple(prefix)
        new_nick = params[0]

        self.logger.debug(
            "%s!%s@%s changed nick to %s" %
            (user + (new_nick,))
        )

        self.event_manager.fire("irc.nick", user, new_nick)

    def irc_TOPIC(self, prefix, params):
        """Called when a new topic is set"""
        super().irc_TOPIC(prefix, params)

        user = self.get_user_tuple(prefix)
        channel = params[0]
        topic = params[1]

        self.logger.debug(
            "%s!%s@%s changed topic in %s to %s" %
            (user + (channel, topic))
        )

        self.event_manager.fire("irc.topic", user, channel, topic)

    def irc_MODE(self, prefix, params):
        """Called when a mode is set on a channel"""
        super().irc_MODE(prefix, params)

        user = self.get_user_tuple(prefix)
        channel = params[0]
        mode = ' '.join(params[1:])

        # Sent by network, not a real user
        if not user:
            self.logger.debug(
                "%s set mode on %s (%s)" % (prefix, channel, mode)
            )
            return

        self.logger.debug(
            "%s!%s@%s set mode on %s (%s)" %
            (user + (channel, mode))
        )

        self.event_manager.fire("irc.mode", user, channel, mode)

    def irc_JOIN(self, prefix, params):
        """Called when a user joins a channel"""
        super().irc_JOIN(prefix, params)

        user = self.get_user_tuple(prefix)
        channel = params[0]

        self.logger.debug(
            "%s!%s@%s joined %s" %
            (user + (channel,))
        )

        self.event_manager.fire("irc.join", user, channel)

    def irc_PART(self, prefix, params):
        """Called when a user parts a channel"""
        super().irc_PART(prefix, params)

        user = self.get_user_tuple(prefix)
        channel = params[0]
        if len(params) == 1:
            reason = None
        else:
            reason = params[1]

        self.logger.debug(
            "%s!%s@%s parted %s (%s)" %
            (user + (channel, reason if reason else "No Message"))
        )

        self.event_manager.fire("irc.part", user, channel, reason)

    def irc_KICK(self, prefix, params):
        """Called when a user is kicked from a channel"""
        super().irc_KICK(prefix, params)

        user = self.get_user_tuple(prefix)
        nick = params[1]
        channel = params[0]
        if len(params) == 2:
            reason = None
        else:
            reason = params[2]

        self.logger.debug(
            "%s!%s@%s kicked %s from %s (%s)" %
            (user + (nick, channel, reason if reason else "No Message"))
        )

        self.event_manager.fire("irc.kick", user, channel, nick, reason)

    def irc_QUIT(self, prefix, params):
        """Called when a user quits the network"""
        super().irc_QUIT(prefix, params)

        user = self.get_user_tuple(prefix)
        if len(params) == 0:
            reason = None
        else:
            reason = params[0]

        self.logger.debug(
            "%s!%s@%s quit (%s)" %
            (user + (reason if reason else "No Message",))
        )

        self.event_manager.fire("irc.quit", user, reason)

    def irc_RPL_WHOREPLY(self, prefix, params):
        """Called for each user in the WHO reply.

        This is the second piece of the `who()` method call. We will add each
        user listed in the reply to a list for the channel that will be sent
        to the channel's Deferred once all users have been listed.
        """
        # Same format as other events (nickname!ident@hostname)
        self.logger.info(params)
        user = user_info(
            params[5],  # nickname
            params[2],  # ident
            params[3],  # hostname
        )
        channel = params[1]

        self._who_cache[channel].append(user)

    def irc_RPL_ENDOFWHO(self, prefix, params):
        """Called when WHO reply is complete.

        This is the final piece of the `who()` method call. This indicates we
        can consider the WHO listing complete, and resolve the Deferred for the
        given channel.
        """
        self.logger.info(params)
        channel = params[1]

        self.logger.info("WHO reply received for %s" % channel)
        for d in self._who_deferreds[channel]:
            d.callback(self._who_cache[channel])

        del self._who_deferreds[channel]

    def irc_unknown(self, prefix, command, params):
        """Called when Twisted doesn't understand an IRC command.

        Keyword arguments:
          prefix -- User sending command. Provided by Twisted.
          command -- Command that wasn't recognized. Provided by Twisted.
          params -- Params for command. Provided by Twisted.
        """
        super().irc_unknown(prefix, command, params)

        # A user has invited us to a channel
        if command == "INVITE":
            # Break down the user into usable groups
            user = self.get_user_tuple(prefix)
            nick = user[0]
            channel = params[1]

            self.logger.debug("%s invited us to %s" % (nick, channel))

            # Fire invite event, so plugins can hook into it
            self.event_manager.fire("irc.invite", user, channel)

            # TODO: Call matching plugin events

    def who(self, channel):
        """Lists the users in a channel.

        Keyword arguments:
          channel -- Channel to list users of.

        Returns:
          Deferred -- A Deferred which will have its callbacks called when
            the WHO response comes back from the server.
        """
        self.logger.info("WHO list requested for %s" % channel)

        d = defer.Deferred()
        if channel not in self._who_deferreds:
            self._who_cache[channel] = []
            self._who_deferreds[channel] = [d]

            # Send the actual WHO command to the server. irc_RPL_WHOREPLY will
            # receive a response when the server sends one.
            self.logger.info("Making WHO request to server")
            self.sendLine("WHO %s" % channel)
        else:
            self._who_deferreds[channel].append(d)

        return d

    def config(self, plugin):
        """Returns a given loaded plugin's config.

        Keyword arguments:
          plugin -- String containing a plugin name.

        Returns:
          dict -- Dictionary containing plugin config.

        Raises:
          ConfigNotFoundError - When config can't be found for the plugin.
        """
        if self.plugin_manager is None:
            self.logger.error(
                "PluginManager has not been initialized! Can't return config "
                "for plugin: %s" % plugin
            )
            raise PluginError("PluginManager has not yet been initialized")

        try:
            config = self.plugin_manager.get_config(plugin)
        except ConfigNotFoundError:
            # Log and raise the exception again
            self.logger.exception(
                "Couldn't find config for plugin: %s" % plugin
            )
            raise

        return config

    def sendMsg(self, channel, message, length=None):
        """Wrapper command to send messages.

        Keyword arguments:
          channel -- Channel to send message to.
          message -- Message to send.
          length -- Length of message. Twisted will calculate if None given.
        """
        self.logger.info("Sending in %s: %s" % (channel, message))
        self.msg(channel, message, length)

    def send(self, message):
        """Send a raw message to the server.

        Keyword arguments:
          message -- Message to send.
        """
        self.logger.info("Sending to server: %s" % message)
        self.sendLine(message)

    def disconnect(self, message=''):
        """Wrapper command to quit Cardinal.

        Keyword arguments:
          message -- Message to insert into QUIT, if any.
        """
        self.logger.info("Disconnecting from network")
        self.plugin_manager.unload_all()
        self.factory.disconnect = True
        self.quit(message)

    def get_db(self, name, network_specific=True, default=None):
        if default is None:
            default = {}

        db_path = os.path.join(self.storage_path, 'database', name + (
            '-{}'.format(self.network) if network_specific else '') +
            '.json')

        if db_path not in self.db_locks:
            self.db_locks[db_path] = UNLOCKED

        @contextmanager
        def db():
            if self.db_locks[db_path] == LOCKED:
                raise LockInUseError('DB {} locked'.format(db_path))

            self.db_locks[db_path] = LOCKED

            try:
                if not os.path.exists(db_path):
                    with open(db_path, 'w') as f:
                        json.dump(default, f)

                # Load the DB as JSON, use it, then save the result
                with open(db_path, 'r+') as f:
                    database = json.load(f)

                    yield database

                    f.seek(0)
                    f.truncate()
                    json.dump(database, f)
            finally:
                self.db_locks[db_path] = UNLOCKED

        return db

    @staticmethod
    def get_user_tuple(string):
        user = re.match(USER_REGEX, string)
        if user:
            return user_info(user.group(1), user.group(2), user.group(3))
        return user


class CardinalBotFactory(protocol.ClientFactory):
    """The interface between Cardinal and the Twisted library"""

    protocol = CardinalBot
    """Tells Twisted to look at the CardinalBot class for a client"""

    MINIMUM_RECONNECTION_WAIT = 10
    """Minimum time in seconds before reconnection attempt"""

    MAXIMUM_RECONNECTION_WAIT = 300
    """Maximum time in connections before reconnection attempt"""

    @property
    def reactor(self):
        return getattr(self, '_reactor', reactor)

    def __init__(self,
                 network,
                 server_password,
                 server_commands,
                 channels,
                 nickname,
                 password,
                 username,
                 realname,
                 plugins,
                 blacklist,
                 storage):
        """Boots the bot, triggers connection, and initializes logging.

        Keyword arguments:
          network -- A string containing the server to connect to.
          channels -- A list of channels to connect to.
          server_password - A string containing a password for the server.
          server_commands - A list of raw commands to send to the server.
          nickname -- A string with the nick to connect as.
          password -- A string with NickServ password, if any.
          username -- A string with the ident to be used.
          realname -- A string containing the real name field.
          plugins -- A list of plugins to load on boot.
          blacklist -- A dict mapping plugins to lists of blacklisted channels.
          storage -- A string containing path to storage directory.
        """

        if server_commands is None:
            server_commands = []

        if plugins is None:
            plugins = []

        if channels is None:
            channels = []

        if blacklist is None:
            blacklist = {}

        self.logger = logging.getLogger(__name__)
        self.network = network.lower()
        self.server_password = server_password
        self.server_commands = server_commands
        self.channels = channels
        self.nickname = nickname
        self.password = password
        self.username = username
        self.realname = realname
        self.plugins = plugins
        self.blacklist = blacklist
        self.storage_path = storage

        # Register SIGINT handler, so we can close the connection cleanly
        signal.signal(signal.SIGINT, self._sigint)

        # Cardinal will set an instance of itself here later
        self.cardinal = None

        # This will be set to True when we don't want to trigger reconnection
        # logic.
        self.disconnect = False

        # The time we first connected to the network with Cardinal
        self.booted = datetime.now()

        # Used for backing off when reconnecting
        self.last_reconnection_wait = None

    def _sigint(self, signal, frame):
        """Called when a SIGINT is received.

        Set disconnect to true since this was user-triggered, and make Cardinal
        send a valid IRC QUIT.
        """
        self.disconnect = True
        if self.cardinal:
            self.cardinal.quit('Received SIGINT.')

    def clientConnectionLost(self, connector, reason):
        """Called when we lose connection to the server.

        Keyword arguments:
          connector -- Twisted IRC connector. Provided by Twisted.
          reason -- Reason for disconnect. Provided by Twisted.
        """
        # This flag tells us if Cardinal was told to disconnect by a user. If
        # not, we'll attempt to reconnect.
        if not self.disconnect:
            self.logger.info(
                "Connection lost (%s), reconnecting in %d seconds." %
                (reason, self.MINIMUM_RECONNECTION_WAIT)
            )

            # Reset the last reconnection wait time since this is the first
            # time we've disconnected since a successful connection and then
            # wait before connecting.
            self.last_reconnection_wait = self.MINIMUM_RECONNECTION_WAIT
            deferLater(
                self.reactor,
                self.last_reconnection_wait,
                connector.connect
            )
        else:
            self.logger.info(
                "Disconnected successfully (%s), quitting." % reason
            )

            self.reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        """Called when a connection attempt fails.

        Keyword arguments:
          connector -- Twisted IRC connector. Provided by Twisted.
          reason -- Reason connection failed. Provided by Twisted.
        """
        # If we disconnected on our first connection attempt, then we don't
        # need to calculate a wait time, we can just use the minimum time
        if not self.last_reconnection_wait:
            wait_time = self.MINIMUM_RECONNECTION_WAIT
        else:
            # We'll attempt to reconnect after waiting twice as long as the
            # last time we waited, unless it exceeds the maximum wait time, in
            # which case we'll wait that long instead
            wait_time = self.last_reconnection_wait * 2
            if wait_time > self.MAXIMUM_RECONNECTION_WAIT:
                wait_time = self.MAXIMUM_RECONNECTION_WAIT

        self.logger.info(
            "Could not connect (%s), retrying in %d seconds" %
            (reason, wait_time)
        )

        # Update the last connection wait time, then wait and try to connect
        self.last_reconnection_wait = wait_time
        deferLater(
            self.reactor,
            self.last_reconnection_wait,
            connector.connect
        )
