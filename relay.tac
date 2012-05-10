# -*- mode: python -*-
import ConfigParser
import os
import sys

from twisted.application import service, internet
from twisted.python import log

from ircer import LogBotFactory
from hipbot import make_client

# initialize logging
log.startLogging(sys.stdout)

config = ConfigParser.ConfigParser()
config.read(os.environ.get('IRCER_CONFIG', 'config.ini'))


xmpp_client = make_client(config)

# create factory protocol and application
log.msg('chat name: ', config.get('irc', 'channel'))
log_bot = LogBotFactory(config.get('irc', 'channel'), xmpp_client)
log_bot.protocol.nickname = config.get('irc', 'botnick')

# connect factory to this host and port
irc_client = internet.TCPClient(
    config.get('irc', 'network'),
    config.getint('irc', 'port'),
    log_bot)

application = service.Application('ircer')
xmpp_client.setServiceParent(application)
irc_client.setServiceParent(application)
