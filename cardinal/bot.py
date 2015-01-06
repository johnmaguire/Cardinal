import os
import sys
import time
import signal
import logging
import re
from datetime import datetime

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor

from cardinal.plugins import PluginManager
from cardinal.exceptions import *


class CardinalBot(irc.IRCClient):
    logger = None
    """Logging object for CardinalBot"""

    factory = None
    """Should contain an instance of CardinalBotFactory"""

    network = None
    """Currently connected network (e.g. irc.freenode.net)"""

    @property
    def nickname(self):
        """This is the nickname property of CardinalBot"""
        return self.factory.nickname

    user_regex = re.compile(r'^(.*?)!(.*?)@(.*?)$')
    """Regex for identifying a user's nick, ident, and vhost"""

    plugin_manager = None
    """Instance of PluginManager"""

    storage_path = None
    """Location of storage directory"""

    uptime = None
    """Time that Cardinal connected to the network"""

    booted  = None
    """Time that Cardinal was first launched"""

    reloads = 0
    """Number of plugin reloads performed"""

    def __init__(self):
        """Initializes the logging and sets storage directory"""
        self.logger = logging.getLogger(__name__)

        self.storage_path = os.path.join(
            os.path.dirname(os.path.realpath(sys.argv[0])),
            'storage'
        )

    def signedOn(self):
        """Called once we've connected to a network"""
        self.logger.info("Signed on as %s" % self.nickname)

        # Give the factory access to the bot
        if self.factory is None:
            raise InternalError("Factory must be set on CardinalBot instance")

        # Give the factory the instance it created in case it needs to
        # interface for error handling or metadata retention.
        self.factory.cardinal = self

        # Set the currently connected network
        self.network = self.factory.network

        # Attempt to identify with NickServ, if a password was given
        if self.factory.password:
            self.logger.info("Attempting to identify with NickServ")
            self.msg("NickServ", "IDENTIFY %s" % (self.factory.password,))

        # Create an instance of PluginManager, giving it an instance of ourself
        # to pass to plugins, as well as a list of initial plugins to load.
        self.plugin_manager = PluginManager(self, self.factory.plugins)

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

    def privmsg(self, user, channel, message):
        """Called when we receive a message in a channel or PM.

        Keyword arguments:
          user -- Tuple containing IRC user info. Provided by Twisted.
          channel -- Channel PRIVMSG was received on. Provided by Twisted.
          message -- Message received. Provided by Twisted.
        """
        # Breaks the user up into usable groups:
        #
        # 1 - nick
        # 2 - ident
        # 3 - hostname
        user = re.match(self.user_regex, user)

        self.logger.debug(
            "%s!%s@%s to %s: %s" %
            (user.group(1), user.group(2), user.group(3), channel, message)
        )

        # If the channel is ourselves, this is actually a PM to us, and so
        # we'll update the channel variable to the sender's username to make
        # replying a little easier.
        if channel == self.nickname:
            channel = user.group(1)

        # Attempt to call a command. If it doesn't appear to PluginManager to
        # be a command, this will just fall through. If it matches command
        # syntax but there is no matching command, then we should catch the
        # exception.
        try:
            self.plugin_manager.call_command(user, channel, message)
        except CommandNotFoundError:
            # This is just an info, since anyone can trigger it, not really a
            # bad thing.
            self.logger.info("Unable to find a matching command", exc_info=True)

    def userJoined(self, nick, channel):
        """Called when another user joins a channel we're in.

        Keyword arguments:
          nick -- Nick of user who joined channel. Provided by Twisted.
          channel -- Channel user joined. Provided by Twisted.
        """
        self.logger.debug("%s joined %s" % (nick, channel))

        # TODO: Call matching plugin events

    def userLeft(self, nick, channel):
        """Called when another user leaves a channel we're in.

        Keyword arguments:
          nick -- Nick of user who left channel. Provided by Twisted.
          channel -- Channel user left. Provided by Twisted.
        """
        self.logger.debug("%s parted %s" % (nick, channel))

        # TODO: Call matching plugin events

    def userQuit(self, nick, quitMessage):
        """Called when another user in a channel we're in quits.

        Keyword arguments:
          nick -- Nick of user who quit. Provided by Twisted.
          quitMessage -- Message in QUIT. Provided by Twisted.
        """
        self.logger.debug("%s quit (Reason: %s)" % (nick, quitMessage))

        # TODO: Call matching plugin events

    def userKicked(self, kicked, channel, kicker, message):
        """Called when another user is kicked from a channel we're in.

        Keyword arguments:
          kicked -- Nick of user who was kicked. Provided by Twisted.
          channel -- Channel user was kicked from. Provided by Twisted.
          kicker -- Nick of user who triggered kick. Provided by Twisted.
          message -- Message in KICK. Provided by Twisted.
        """
        self.logger.debug(
            "%s kicked %s from %s (Reason: %s)" %
            (kicker, kicked, channel, message)
        )

        # TODO: Call matching plugin events

    def action(self, user, channel, data):
        """Called when a user does an action message in a channel we're in.

        Keyword arguments:
          user -- Tuple containing IRC user info. Provided by Twisted.
          channel -- Channel ACTION was received on. Provided by Twisted.
          data -- Message in ACTION. Provided by Twisted.
        """
        # Break the user up into usable groups
        user = re.match(self.user_regex, user)

        self.logger.debug(
            "Action on %s: %s!%s@%s %s" %
            (channel, user.group(1), user.group(2), user.group(3), data)
        )

        # TODO: Call matching plugin events

    def topicUpdated(self, nick, channel, newTopic):
        """Called when a user updates a topic in a channel we're in.

        Keyword arguments:
          nick -- Nick of user who updated the topic. Provided by Twisted.
          channel -- Channel TOPIC was received on. Provided by Twisted.
          newTopic -- New channel topic. Provided by Twisted.
        """
        self.logger.debug(
            "Topic updated in %s by %s: %s" % (channel, nick, newTopic)
        )

        # TODO: Call matching plugin events

    def userRenamed(self, oldNick, newNick):
        """Called when a user in a channel we're in changes their nick.

        Keyword arguments:
          oldNick -- User's old nick. Provided by Twisted.
          newNick -- User's new nick. Provided by Twisted.
        """
        self.logger.debug("%s changed nick to %s" % (oldNick, newNick))

        # TODO: Call matching plugin events

    def irc_unknown(self, prefix, command, params):
        """Called when Twisted doesn't understand an IRC command.

        Keyword arguments:
          prefix -- Message before IRC command. Provided by Twisted.
          command -- Command that wasn't recognized. Provided by Twisted.
          params -- Message after IRC command. Provided by Twisted.
        """
        # A user has invited us to a channel
        if command == "INVITE":
            nick = params[0]
            channel = params[1]

            self.logger.debug("%s invited us to %s")

            # TODO: Call matching plugin events

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
        except ConfigNotFoundError, e:
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

    def disconnect(self, message=''):
        """Wrapper command to quit Cardinal.

        Keyword arguments:
          message -- Message to insert into QUIT, if any.
        """
        self.logger.info("Disconnecting from network")
        self.plugin_manager.unload_all()
        self.factory.disconnect = True
        self.quit(message)

# This interfaces CardinalBot with the Twisted library
class CardinalBotFactory(protocol.ClientFactory):
    logger = None
    """Logger object for CardinalBotFactory"""

    protocol = CardinalBot
    """Tells Twisted to look at the CardinalBot class for a client"""

    disconnect = False
    """Keeps track of whether disconnect was triggered by CardinalBot"""

    network = None
    """Network to connect to"""

    nickname = None
    """Nick to connect with"""

    password = None
    """NickServ password, if any"""

    channels = []
    """Channels to join upon connection"""

    plugins = []
    """Plugins to load upon connection"""

    cardinal = None
    """When CardinalBot is started, holds its instance"""

    minimum_reconnection_wait = 10
    """Minimum time in seconds before reconnection attempt"""

    maximum_reconnection_wait = 300
    """Maximum time in connections before reconnection attempt"""

    last_reconnection_wait = None
    """Time in seconds since last reconnection attempt"""

    booted = None
    """Datetime object holding time Cardinal first started up"""

    def __init__(self, network, channels, nickname='Cardinal', password=None, plugins=[]):
        """Boots the bot, triggers connection, and initializes logging.

        Keyword arguments:
          network -- A string containing the server to connect to.
          channels -- A list of channels to connect to.
          nickname -- A string with the nick to connect as.
          password -- A string with NickServ password, if any.
          plugins -- A list of plugins to load on boot.
        """
        self.logger = logging.getLogger(__name__)
        self.network = network.lower()
        self.password = password
        self.channels = channels
        self.nickname = nickname
        self.plugins = plugins

        # Register SIGINT handler, so we can close the connection cleanly
        signal.signal(signal.SIGINT, self._sigint)

        self.booted = datetime.now()

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
                (reason, self.minimum_reconnection_wait)
            )

            # Reset the last reconnection wait time since this is the first
            # time we've disconnected since a successful connection and then
            # wait before connecting.
            self.last_reconnection_wait = self.minimum_reconnection_wait
            time.sleep(self.minimum_reconnection_wait)
            connector.connect()
        else:
            self.logger.info(
                "Disconnected successfully (%s), quitting." % reason
            )

            reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        """Called when a connection attempt fails.

        Keyword arguments:
          connector -- Twisted IRC connector. Provided by Twisted.
          reason -- Reason connection failed. Provided by Twisted.
        """
        # If we disconnected on our first connection attempt, then we don't
        # need to calculate a wait time, we can just use the minimum time
        if not self.last_reconnection_wait:
            wait_time = self.minimum_reconnection_wait
        else:
            # We'll attempt to reconnect after waiting twice as long as the
            # last time we waited, unless it exceeds the maximum wait time, in
            # which case we'll wait that long instead
            wait_time = self.last_reconnection_wait * 2
            if wait_time > self.maximum_reconnection_wait:
                wait_time = self.maximum_reconnection_wait

        self.logger.info(
            "Could not connect (%s), retrying in %d seconds" %
            (reason, wait_time)
        )

        # Update the last connection wait time, then wait and try to connect
        self.last_reconnection_wait = wait_time
        time.sleep(wait_time)
        connector.connect()
