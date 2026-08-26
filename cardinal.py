#!/usr/bin/env python

import os
import sys
import argparse
import logging
import logging.config

from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet import reactor
from twisted.internet.endpoints import HostnameEndpoint, wrapClientTLS
from twisted.internet.ssl import optionsForClientTLS

from cardinal.config import ConfigParser, ConfigSpec
from cardinal.bot import CardinalBotFactory


def setup_logging(config=None):
    if config is None:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.config.dictConfig(config)

    return logging.getLogger(__name__)


if __name__ == "__main__":
    # Create a new instance of ArgumentParser with a description about Cardinal
    arg_parser = argparse.ArgumentParser(description="""
Cardinal IRC bot

A Twisted IRC bot designed to be simple to use and and easy to extend.

https://github.com/JohnMaguire/Cardinal
""", formatter_class=argparse.RawDescriptionHelpFormatter)

    arg_parser.add_argument('config', metavar='config',
                            help='custom config location')

    # Parse command-line arguments
    args = arg_parser.parse_args()
    config_file = args.config

    # Define the config spec and create a parser for our internal config
    spec = ConfigSpec()
    spec.add_option('nickname', str, 'Cardinal')
    spec.add_option('password', str, None)
    spec.add_option('username', str, None)
    spec.add_option('realname', str, None)
    spec.add_option('network', str, 'irc.darkscience.net')
    spec.add_option('port', int, 6697)
    spec.add_option('server_password', str, None)
    spec.add_option('server_commands', list, [])
    spec.add_option('ssl', bool, True)
    spec.add_option('storage', str, os.path.join(
        os.path.dirname(os.path.realpath(sys.argv[0])),
        'storage'
    ))
    spec.add_option('channels', list, ['#bots'])
    spec.add_option('censored_words', dict, {})
    spec.add_option('plugins', list, [
        "admin",
        "github",
        "google",
        "help",
        "join_on_invite",
        "lastfm",
        "ping",
        "remind",
        "sed",
        "seen",
        "timezone",
        "urbandict",
        "urls",
        "weather",
        "wikipedia",
        "youtube"
    ])
    spec.add_option('blacklist', dict, {})
    spec.add_option('logging', dict, None)

    parser = ConfigParser(spec)

    # Load config file
    try:
        config = parser.load_config(config_file)
    except Exception:
        # Need to setup a logger early
        logger = setup_logging()
        logger.exception("Unable to load config: {}".format(config_file))
        sys.exit(1)

    # Config loaded, setup the logger
    logger = setup_logging(config['logging'])

    logger.info("Config loaded: {}".format(config_file))

    # Determine storage directory
    if config['storage'] is not None:
        if config['storage'].startswith('/'):
            config['storage'] = config['storage']
        else:
            config['storage'] = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                config['storage']
            )

        logger.info("Storage path: {}".format(config['storage']))

        directories = [
            os.path.join(config['storage'], 'database'),
            os.path.join(config['storage'], 'logs'),
        ]

        for directory in directories:
            if not os.path.exists(directory):
                logger.info(
                    "Initializing storage directory: {}".format(directory))
                os.makedirs(directory)

    # If no username is supplied, default to nickname
    if config['username'] is None:
        config['username'] = config['nickname']

    # Instance a new factory, and connect with/without SSL
    logger.debug("Instantiating CardinalBotFactory")
    factory = CardinalBotFactory(config['network'],
                                 config['server_password'],
                                 config['server_commands'],
                                 config['channels'],
                                 config['nickname'],
                                 config['password'],
                                 config['username'],
                                 config['realname'],
                                 config['plugins'],
                                 config['censored_words'],
                                 config['blacklist'],
                                 config['storage'])

    endpoint = HostnameEndpoint(reactor, config['network'], config['port'])
    if config['ssl']:
        logger.info(
            "Connecting over TLS to %s:%d" %
            (config['network'], config['port'])
        )

        endpoint = wrapClientTLS(
            optionsForClientTLS(config['network']), endpoint)
    else:
        logger.info(
            "Connecting over plaintext to %s:%d" %
            (config['network'], config['port'])
        )

    # ClientService reconnects with exponential backoff whenever the
    # connection drops or an attempt fails, until stopService is called
    service = ClientService(
        endpoint,
        factory,
        retryPolicy=backoffPolicy(
            initialDelay=CardinalBotFactory.MINIMUM_RECONNECTION_WAIT,
            maxDelay=CardinalBotFactory.MAXIMUM_RECONNECTION_WAIT,
            factor=2.0,
        ),
    )
    factory.service = service
    service.startService()

    # Run the Twisted reactor
    reactor.run()
