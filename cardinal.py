#!/usr/bin/env python

import os
import logging
import json
import argparse
from getpass import getpass

from twisted.internet import reactor
from cardinal.config import ConfigParser
from cardinal.bot import CardinalBotFactory

# If this file is being run directly, set the logging level, load config file,
# parse command-line arguments, and instance and run CardinalBot
if __name__ == "__main__":
    # Set logging to info by default
    logging.basicConfig(level=logging.INFO)

    parser = ConfigParser()

    # First attempt to load config.json for config options
    logging.info("Looking for and attempting to load config.json")
    config = parser.load_config('config.json')

    # Parse command-line arguments last, as they should override both project
    # defaults and the user config (if available)
    logging.info("Parsing command-line arguments")
    argparser = parser.generate_argparser()
    args   = argparser.parse_args()

    # If the password flag was set, let the user safely type in their password
    if args.password:
        password = getpass('NickServ password: ')
    else:
        password = config['password']

    # Instance a new factory, and connect with/without SSL
    factory = CardinalBotFactory(args.network, args.channels, args.nickname, password, args.plugins)
    if not args.ssl:
        reactor.connectTCP(args.network, args.port, factory)
    else:
        from twisted.internet import ssl
        reactor.connectSSL(args.network, args.port, factory, ssl.ClientContextFactory())

    # Run the Twisted reactor
    reactor.run()
