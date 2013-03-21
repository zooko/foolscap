
from twisted.trial import unittest
from twisted.internet import defer
from foolscap.api import UnauthenticatedTub, Tub
from foolscap.test.common import HelperTarget, crypto_available
from foolscap.eventual import flushEventualQueue


class ConnectToSelf(unittest.TestCase):

    def setUp(self):
        self.services = []

    def requireCrypto(self):
        if not crypto_available:
            raise unittest.SkipTest("crypto not available")

    def startTub4(self, tub):
        self.services = [tub]
        for s in self.services:
            s.startService()
            l = s.listenOn("tcp:0:interface=127.0.0.1")
            s.setLocation("127.0.0.1:%d" % l.getPortnum())

    def startTub6(self, tub):
        self.services = [tub]
        for s in self.services:
            s.startService()
            l = s.listenOn("tcp6:0:interface=[::1]")
            s.setLocation("ipv6:[::1]:%d" % l.getPortnum())

    def tearDown(self):
        d = defer.DeferredList([s.stopService() for s in self.services])
        d.addCallback(flushEventualQueue)
        return d

    def testConnectUnauthenticated4(self):
        tub = UnauthenticatedTub()
        self.startTub4(tub)
        target = HelperTarget("bob")
        target.obj = "unset"
        url = tub.registerReference(target)
        # can we connect to a reference on our own Tub?
        d = tub.getReference(url)
        def _connected(ref):
            return ref.callRemote("set", 12)
        d.addCallback(_connected)
        def _check(res):
            self.failUnlessEqual(target.obj, 12)
        d.addCallback(_check)

        def _connect_again(res):
            target.obj = None
            return tub.getReference(url)
        d.addCallback(_connect_again)
        d.addCallback(_connected)
        d.addCallback(_check)

        return d

    def testConnectUnauthenticated6(self):
        tub = UnauthenticatedTub()
        self.startTub6(tub)
        target = HelperTarget("bob")
        target.obj = "unset"
        url = tub.registerReference(target)
        # can we connect to a reference on our own Tub?
        d = tub.getReference(url)
        def _connected(ref):
            return ref.callRemote("set", 12)
        d.addCallback(_connected)
        def _check(res):
            self.failUnlessEqual(target.obj, 12)
        d.addCallback(_check)

        def _connect_again(res):
            target.obj = None
            return tub.getReference(url)
        d.addCallback(_connect_again)
        d.addCallback(_connected)
        d.addCallback(_check)

        return d

    def testConnectAuthenticated4(self):
        self.requireCrypto()
        tub = Tub()
        self.startTub4(tub)
        target = HelperTarget("bob")
        target.obj = "unset"
        url = tub.registerReference(target)
        # can we connect to a reference on our own Tub?
        d = tub.getReference(url)
        def _connected(ref):
            return ref.callRemote("set", 12)
        d.addCallback(_connected)
        def _check(res):
            self.failUnlessEqual(target.obj, 12)
        d.addCallback(_check)
        def _connect_again(res):
            target.obj = None
            return tub.getReference(url)
        d.addCallback(_connect_again)
        d.addCallback(_connected)
        d.addCallback(_check)
        return d

    def testConnectAuthenticated6(self):
        self.requireCrypto()
        tub = Tub()
        self.startTub6(tub)
        target = HelperTarget("bob")
        target.obj = "unset"
        url = tub.registerReference(target)
        # can we connect to a reference on our own Tub?
        d = tub.getReference(url)
        def _connected(ref):
            return ref.callRemote("set", 12)
        d.addCallback(_connected)
        def _check(res):
            self.failUnlessEqual(target.obj, 12)
        d.addCallback(_check)
        def _connect_again(res):
            target.obj = None
            return tub.getReference(url)
        d.addCallback(_connect_again)
        d.addCallback(_connected)
        d.addCallback(_check)
        return d
