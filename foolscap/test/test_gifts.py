
from twisted.trial import unittest
from twisted.internet import defer
from twisted.internet.error import ConnectionDone
from foolscap import Tub
from foolscap.referenceable import RemoteReference
from foolscap.test.common import HelperTarget

def ignoreConnectionDone(f):
    f.trap(ConnectionDone)
    return None

class Gifts(unittest.TestCase):
    # Here we test the three-party introduction process as depicted in the
    # classic Granovetter diagram. Alice has a reference to Bob and another
    # one to Carol. Alice wants to give her Carol-reference to Bob, by
    # including it as the argument to a method she invokes on her
    # Bob-reference.

    debug = False

    def setUp(self):
        self.services = [Tub(), Tub(), Tub()]
        self.tubA, self.tubB, self.tubC = self.services
        for s in self.services:
            s.startService()
            l = s.listenOn("tcp:0:interface=127.0.0.1")
            s.setLocation("localhost:%d" % l.getPortnum())

    def tearDown(self):
        return defer.DeferredList([s.stopService() for s in self.services])

    def createCharacters(self):
        self.alice = HelperTarget("alice")
        self.bob = HelperTarget("bob")
        self.bob_url = self.tubB.registerReference(self.bob)
        self.carol = HelperTarget("carol")
        self.carol_url = self.tubC.registerReference(self.carol)

    def createInitialReferences(self):
        # we must start by giving Alice a reference to both Bob and Carol.
        if self.debug: print "Alice gets Bob"
        d = self.tubA.getReference(self.bob_url)
        def _aliceGotBob(abob):
            if self.debug: print "Alice got bob"
            self.abob = abob # Alice's reference to Bob
            if self.debug: print "Alice gets carol"
            d = self.tubA.getReference(self.carol_url)
            return d
        d.addCallback(_aliceGotBob)
        def _aliceGotCarol(acarol):
            if self.debug: print "Alice got carol"
            self.acarol = acarol # Alice's reference to Carol
        d.addCallback(_aliceGotCarol)
        return d

    def testGift(self):
        #defer.setDebugging(True)
        self.createCharacters()
        d = self.createInitialReferences()
        def _introduce(res):
            d2 = self.bob.waitfor()
            if self.debug: print "Alice introduces Carol to Bob"
            # send the gift. This might not get acked by the time the test is
            # done and everything is torn down, so explicitly silence any
            # ConnectionDone error that might result. When we get
            # callRemoteOnly(), use that instead.
            d3 = self.abob.callRemote("set", obj=(self.alice, self.acarol))
            d3.addErrback(ignoreConnectionDone)
            return d2 # this fires with the gift that bob got
        d.addCallback(_introduce)
        def _bobGotCarol((balice,bcarol)):
            if self.debug: print "Bob got Carol"
            self.bcarol = bcarol
            if self.debug: print "Bob says something to Carol"
            d2 = self.carol.waitfor()
            # handle ConnectionDone as described before
            d3 = self.bcarol.callRemote("set", obj=12)
            d3.addErrback(ignoreConnectionDone)
            return d2
        d.addCallback(_bobGotCarol)
        def _carolCalled(res):
            if self.debug: print "Carol heard from Bob"
            self.failUnlessEqual(res, 12)
        d.addCallback(_carolCalled)
        return d


    def testOrdering(self):
        self.createCharacters()
        self.bob.calls = []
        d = self.createInitialReferences()
        def _introduce(res):
            # we send three messages to Bob. The second one contains the
            # reference to Carol.
            dl = []
            dl.append(self.abob.callRemote("append", obj=1))
            dl.append(self.abob.callRemote("append", obj=self.acarol))
            dl.append(self.abob.callRemote("append", obj=3))
            return defer.DeferredList(dl)
        d.addCallback(_introduce)
        def _checkBob(res):
            # this runs after all three messages have been acked by Bob
            self.failUnlessEqual(len(self.bob.calls), 3)
            self.failUnlessEqual(self.bob.calls[0], 1)
            self.failUnless(isinstance(self.bob.calls[1], RemoteReference))
            self.failUnlessEqual(self.bob.calls[2], 3)
        d.addCallback(_checkBob)
        return d

    # this was used to alice's reference to carol (self.acarol) appeared in
    # alice's gift table at the right time, to make sure that the
    # RemoteReference is kept alive while the gift is in transit. The whole
    # introduction pattern is going to change soon, so it has been disabled
    # until I figure out what the new scheme ought to be asserting.

    def OFF_bobGotCarol(self, (balice,bcarol)):
        if self.debug: print "Bob got Carol"
        # Bob has received the gift
        self.bcarol = bcarol

        # wait for alice to receive bob's 'decgift' sequence, which was sent
        # by now (it is sent after bob receives the gift but before the
        # gift-bearing message is delivered). To make sure alice has received
        # it, send a message back along the same path.
        def _check_alice(res):
            if self.debug: print "Alice should have the decgift"
            # alice's gift table should be empty
            brokerAB = self.abob.tracker.broker
            self.failUnlessEqual(brokerAB.myGifts, {})
            self.failUnlessEqual(brokerAB.myGiftsByGiftID, {})
        d1 = self.alice.waitfor()
        d1.addCallback(_check_alice)
        # the ack from this message doesn't always make it back by the time
        # we end the test and hang up the connection. That connectionLost
        # causes the deferred that this returns to errback, triggering an
        # error, so we must be sure to discard any error from it. TODO: turn
        # this into balice.callRemoteOnly("set", 39), which will have the
        # same semantics from our point of view (but in addition it will tell
        # the recipient to not bother sending a response).
        balice.callRemote("set", 39).addErrback(lambda ignored: None)

        if self.debug: print "Bob says something to Carol"
        d2 = self.carol.waitfor()
        d = self.bcarol.callRemote("set", obj=12)
        d.addCallback(lambda res: d2)
        d.addCallback(self._carolCalled)
        d.addCallback(lambda res: d1)
        return d

