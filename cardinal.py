#!/usr/bin/env python

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

import argparse

from twisted.internet import reactor
from CardinalBot import CardinalBotFactory

DEFAULT_NICKNAME = 'Cardinal'
DEFAULT_NETWORK = 'irc.darchoods.net'
DEFAULT_PORT = 6667
DEFAULT_CHANNELS = ('#bots',)
DEFAULT_PLUGINS = (
    'ping',
    'urls',
    'weather',
#    'admin',
#    'lastfm',
)

parser = argparse.ArgumentParser(description='Cardinal IRC bot')
parser.add_argument('-n', '--nickname', metavar='nickname', default=DEFAULT_NICKNAME,
                    help='nickname to connect as', required=False)

parser.add_argument('-i', '--network', metavar='network', default=DEFAULT_NETWORK,
                    help='network to connect to', required=False)
parser.add_argument('-o', '--port', metavar='port', default=DEFAULT_PORT, type=int,
                    help='network port to connect to', required=False)

parser.add_argument('-c', '--channels', metavar='channel', dest='channels',
                    default=DEFAULT_CHANNELS, nargs='*', help='list of channels to connect to on startup',
                    required=False)
parser.add_argument('-p', '--plugins', metavar='plugin', dest='plugins',
                    default=DEFAULT_PLUGINS, nargs='*', help='list of plugins to load on startup',
                    required=False)

parser.add_argument('-s', '--ssl', dest='ssl', action='store_true', default=False,
                    help='you must set this flag for SSL connections')

if __name__ == "__main__":
    args = parser.parse_args()
    factory = CardinalBotFactory(args.channels, args.nickname, args.plugins)

    if not args.ssl:
        from twisted.internet import ssl
        reactor.connectTCP(args.network, args.port, factory)
    else:
        reactor.connectSSL(args.network, args.port, factory, ssl.ClientContextFactory())
    reactor.run()
