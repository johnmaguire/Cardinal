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
    factory = None
    """Should contain an instance of `CardinalBotFactory`"""

    network = None
    """Currently connected network (e.g. irc.darchoods.net)"""

    @property
    def nickname(self):
        """This is the `nickname` property of CardinalBot"""
        return self.factory.nickname

    user_regex = re.compile(r'^(.*?)!(.*?)@(.*?)$')
    """Regex for identifying a user's nick, ident, and vhost"""

    plugin_manager = None
    """Holds an instance of `PluginManager`"""

    # Some meta info, keeping track of the uptime of the bot, the boot time
    # (when the first instance of CardinalBot was brought online), and the
    # number of reloads performed.
    uptime  = None
    booted  = None
    reloads = 0

    def signedOn(self):
        """Called once we've connected to a network"""
        logging.info("Signed on as %s" % self.nickname)

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
            logging.info("Attempting to identify with NickServ")
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
        """Called when we join a channel"""
        logging.info("Joined %s" % channel)

    def privmsg(self, user, channel, message):
        """Called when we receive a message in a channel or PM"""
        # Breaks the user up into usable groups:
        #
        # 1 - nick
        # 2 - ident
        # 3 - hostname
        user = re.match(self.user_regex, user)

        logging.debug(
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
            logging.info("Unable to find a matching command", exc_info=True)

    def userJoined(self, nick, channel):
        """Called when another user joins a channel we're in"""
        logging.debug("%s joined %s" % (nick, channel))

        # TODO: Call matching plugin events

    def userLeft(self, nick, channel):
        """Called when another user leaves a channel we're in"""
        logging.debug("%s parted %s" % (nick, channel))

        # TODO: Call matching plugin events

    def userQuit(self, nick, quitMessage):
        """Called when another user in a channel we're in quits"""
        logging.debug("%s quit (Reason: %s)" % (nick, quitMessage))

        # TODO: Call matching plugin events

    def userKicked(self, kicked, channel, kicker, message):
        """Called when another user is kicked from a channel we're in"""
        logging.debug("%s kicked %s from %s (Reason: %s)" % (kicker, kicked, channel, message))

        # TODO: Call matching plugin events

    def action(self, user, channel, data):
        """Called when a user does an action message in a channel we're in"""
        # Break the user up into usable groups
        user = re.match(self.user_regex, user)

        logging.debug(
            "Action on %s: %s!%s@%s %s" % 
            (channel, user.group(1), user.group(2), user.group(3), data)
        )

        # TODO: Call matching plugin events

    def topicUpdated(self, nick, channel, newTopic):
        """Called when a user updates a topic in a channel we're in"""
        logging.debug(
            "Topic updated in %s by %s: %s" % (channel, nick, newTopic)
        )

        # TODO: Call matching plugin events

    def userRenamed(self, oldNick, newNick):
        """Called when a user in a channel we're in changes their nick"""
        logging.debug("%s changed nick to %s" % (oldNick, newNick))

        # TODO: Call matching plugin events

    def irc_unknown(self, prefix, command, params):
        """Called when Twisted doesn't understand an IRC command"""
        # A user has invited us to a channel
        if command == "INVITE":
            nick = params[0]
            channel = params[1]

            logging.debug("%s invited us to %s")

            # TODO: Call matching plugin events

    def disconnect(self, message=''):
        """Wrapper command to quit Cardinal"""
        logging.info("Disconnecting from network")
        self.plugin_manager.unload_all()
        self.factory.disconnect = True
        self.quit(message)

    # This is a wrapper command to send messages
    def sendMsg(self, channel, message, length=None):
        """Wrapper command to send messages"""
        logging.info("Sending in %s: %s" % (channel, message))
        self.msg(channel, message, length)

# This interfaces CardinalBot with the Twisted library
class CardinalBotFactory(protocol.ClientFactory):
    protocol = CardinalBot

    # Whether disconnect.quit() was called.
    disconnect = False

    # The network Cardinal has connected to
    network = None

    # The nickname Cardinal has connected as
    nickname = None

    # The password for Cardinal to identify with, if any
    password = None

    # List of channels for CardinalBot to join
    channels = []

    # List of plugins to start CardinalBot with
    plugins = []

    # The instance of CardinalBot, which will be set by CardinalBot
    cardinal = None

    # The minimum time to wait before attempting to reconnect from an
    # unexpected disconnection (in seconds)
    minimum_reconnection_wait = 10

    # The maximum amount of time to wait before attempting to reconnect from an
    # unexpected disconnection (in seconds)
    maximum_reconnection_wait = 3600

    # The amount of time we waited before attempting to reconnect last
    last_reconnection_wait = None

    # The time the first instance of CardinalBot was brought online
    booted = None

    def __init__(self, network, channels, nickname='Cardinal', password=None, plugins=[]):
        self.network = network.lower()
        self.password = password
        self.channels = channels
        self.nickname = nickname
        self.plugins = plugins

        signal.signal(signal.SIGINT, self._sigint)

        self.booted = datetime.now()

    def _sigint(self, signal, frame):
        self.disconnect = True
        if self.cardinal:
            self.cardinal.quit('Received SIGINT.')

    def clientConnectionLost(self, connector, reason):
        # This flag tells us whether Cardinal was supposed to disconnect or not
        if not self.disconnect:
            logging.info(
                "Connection lost (%s), reconnecting in %d seconds." %
                (reason, self.minimum_reconnection_wait)
            )

            # Reset the last reconnection wait time since this is the first
            # time we've disconnected since a successful connection and then
            # wait before connecting
            self.last_reconnection_wait = self.minimum_reconnection_wait
            time.sleep(self.minimum_reconnection_wait)
            connector.connect()
        else:
            logging.info(
                "Disconnected successfully (%s), quitting." % reason
            )

            reactor.stop()

    def clientConnectionFailed(self, connector, reason):
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

        logging.info(
            "Could not connect (%s), retrying in %d seconds" %
            (reason, wait_time)
        )

        # Update the last connection wait time, then wait and try to connect
        self.last_reconnection_wait = wait_time
        time.sleep(wait_time)
        connector.connect()
