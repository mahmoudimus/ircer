import datetime

from twisted.words.protocols import irc
from twisted.internet import protocol
from twisted.python import log

from hipbot import make_client, HipBot


NOW = datetime.datetime.now


class LogBot(irc.IRCClient):
    """A logging IRC bot."""

    nickname = 'yomom'

    @property
    def hipbot(self):
        # ugh.
        for handler in self.factory.xmpp_client.handlers:
            if isinstance(handler, HipBot):
                return handler

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.hipbot.relay("[connected at %sZ]" % NOW().isoformat())

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.hipbot.relay("[disconnected at %sZ]" % NOW().isoformat())

    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.hipbot.relay("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.hipbot.relay("<%s> %s" % (user, msg), user_nick=user)

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            msg = "It isn't nice to whisper!  Play nice with the group."
            self.msg(user, msg)
            return

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            msg = "%s: I am a log bot" % user
            self.msg(channel, msg)

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.hipbot.relay("* %s %s" % (user, msg), user_nick=user)

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.hipbot.relay("%s is now known as %s" % (old_nick, new_nick),
                          quietly=True)

    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """
    protocol = LogBot

    def __init__(self, channel, xmpp_client):
        self.channel = channel
        self.xmpp_client = xmpp_client
