# -*- mode: python -*-
import ConfigParser
import os

from twisted.application import service

from hipbot import make_client

config = ConfigParser.ConfigParser()
config.read(os.environ.get('IRCER_CONFIG', 'config.ini'))

xmpp_client = make_client(config)
application = service.Application('hipbot')
xmpp_client.setServiceParent(application)
