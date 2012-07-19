import datetime

from twisted.internet import defer
from twisted.python import log
from twisted.words.protocols.jabber import jid
from wokkel import muc
from wokkel.client import XMPPClient
from wokkel.xmppim import AvailabilityPresence

from keepalive import KeepAlive


class HipBot(muc.MUCClient):

    def __init__(self, server, room, nick, stfu_minutes):
        super(HipBot, self).__init__()
        self.connected = False
        self.server = server
        self.room = room
        self.nick = nick
        self.stfu_minutes = stfu_minutes
        self.room_jid = jid.internJID(
            '{room}@{server}/{nick}'.format(
                room=self.room,
                server=self.server,
                nick=self.nick))
        self.last = {}
        self.last_spoke = None
        self.activity = None

    def _getLast(self, nick):
        return self.last.get(nick.lower())

    def _setLast(self, user):
        user.last = datetime.datetime.now()
        self.last[user.nick.lower()] = user
        self.activity = user

    def connectionInitialized(self):
        """The bot has connected to the xmpp server, now try to join the room.
        """
        super(HipBot, self).connectionInitialized()
        self.join(self.room_jid, self.nick).addCallback(self.initRoom)
        self.connected = True

    @defer.inlineCallbacks
    def initRoom(self, room):
        """Configure the room if we just created it.
        """

        if room.locked:
            config_form = yield self.getConfigureForm(self.room_jid.userhost())

            # set config default
            config_result = yield self.configure(self.room_jid.userhost())

    def _stfu(self, user_nick=None):
        """Returns True if we don't want to prefix the message with @all which
        will stop the bot from push notifying HipChat users
        """
        right_now = datetime.datetime.now()
        last_spoke = self.last_spoke
        self.last_spoke = right_now
        threshold = right_now - datetime.timedelta(minutes=self.stfu_minutes)
        if last_spoke and last_spoke > threshold:
            return True
        return False

    def relay(self, msg, user_nick=None, quietly=False):
        muc.Room(self.room_jid, self.nick)

        if not quietly and not self._stfu(user_nick):
            msg = '@all ' + msg

        if not self.connected:
            log.msg('Not connected yet, ignoring msg: %s' % msg)
        self.groupChat(self.room_jid, msg)

    def userJoinedRoom(self, room, user):
        """If a user joined a room, make sure they are in the last dict
        """
        self._setLast(user)

    def userLeftRoom(self, room, user):
        self._setLast(user)

    def receivedGroupChat(self, room, user, message):
        # check if this message addresses the bot
        cmd = None
        # value error means it was a one word body
        cmd = message.body
        cmd = cmd.replace('!', '')

        method = getattr(self, 'cmd_' + cmd, None)

        if method:
            method(room, user.nick)

        # log last message
        user.last_message = message.body
        self._setLast(user)

    def cmd_hello(self, room, user_nick):
        self.groupChat(self.room_jid, 'Hello there: %s' % user_nick)

    def cmd_last(self, room, user_nick):
        """
        """
        if user_nick is None:
            # show last person to do something
            self._sendLast(room, self.activity)
        else:
            u = self._getLast(user_nick)
            if u:
                self._sendLast(room, u)
            else:
                self.groupChat(
                    self.room_jid,
                    'Sorry %s, That person is unknown to me.' % (user_nick,))

    def _sendLast(self, room, user):
        """ Grab last information from user and room and send it to the room.
        """
        last_message = getattr(user, 'last_message', '')
        last_stamp = getattr(user, 'last', '')

        if room.inRoster(user):
            message = ("""%s is in this room and said '%s' at %s.""" % (
                user.nick, last_message, last_stamp
            ))
        else:
            message = ("""%s left this room at %s and last said '%s'.""" % (
                user.nick, last_stamp, last_message
            ))

        self.groupChat(self.room_jid, message)


def make_client(config):

    keepalive = KeepAlive()
    keepalive.interval = config.getint('hipchat', 'keepalive.interval')
    xmppclient = XMPPClient(
        jid.internJID(config.get('hipchat', 'jabber_id')),
        config.get('hipchat', 'password')
    )
    xmppclient.logTraffic = config.getboolean('hipchat', 'logtraffic')

    mucbot = HipBot(
        config.get('hipchat', 'server'),
        config.get('hipchat', 'channel'),
        config.get('hipchat', 'botnick'),
        config.get('hipchat', 'stfu_minutes'))
    mucbot.setHandlerParent(xmppclient)
    keepalive.setHandlerParent(xmppclient)

    return xmppclient


if __name__ == '__main__':
    import ConfigParser
    import os
    config = ConfigParser.ConfigParser()
    config.read(os.environ.get('IRCER_CONFIG', 'config.ini'))

    client = make_client(config)
    client.startService()

    from twisted.internet import reactor
    reactor.run()
