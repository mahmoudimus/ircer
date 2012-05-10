from twisted.python import log
from twisted.internet import task

from wokkel.subprotocols import XMPPHandler

# From https://mailman.ik.nu/pipermail/twisted-jabber/2008-October/000171.html


class KeepAlive(XMPPHandler):

    interval = 300
    lc = None

    def connectionInitialized(self):
        self.lc = task.LoopingCall(self.ping)
        self.lc.start(self.interval)

    def connectionLost(self, *args):
        if self.lc:
            self.lc.stop()

    def ping(self):
        log.msg("Stayin' alive")
        self.send(" ")
