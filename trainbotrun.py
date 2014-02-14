#!/usr/bin/env python

import irc.client
import irc.bot
import sys
import time
from threading import Thread
import trainbotbrain
from trainbotpass import password, ownernick

channel = sys.argv[1]

irc.client.ServerConnection.buffer_class.errors = 'replace'

class reloader(irc.bot.SingleServerIRCBot):
    def __init__(self, serverspec, nick):
        irc.bot.SingleServerIRCBot.__init__(self, serverspec, nick, nick)
        self.nick = nick
        self.botclassname = nick + "bot"
        self.brain = getattr(trainbotbrain, self.botclassname)()
        self.broken = False
 
    def on_welcome(self, c, event):
        print c.nickname , "is now online"
        c.privmsg("nickserv", "identify " + password)
        c.join(channel)

    def on_pubmsg(self, c, event):
        if not self.broken:
            try:
                self.brain.on_pubmsg(c, event)
            except Exception as thisbroke:
                self.errorhandle(thisbroke, c)

    def on_privmsg(self, c, event):
        if event.source.nick == ownernick and event.arguments[0] == "lern":
            try:
                reload(trainbotbrain)
                self.brain = getattr(trainbotbrain, self.botclassname)()
                self.broken = False
            except Exception as thisbroke:
                self.errorhandle(thisbroke, c)
        elif not self.broken:
            try:
                self.brain.on_privmsg(c, event)
            except Exception as thisbroke:
                self.errorhandle(thisbroke, c)

    def errorhandle(self, thisbroke, c):
        c.privmsg(ownernick, "halp")
        print ("%s had an error of type %s: %s" % (self.nick, type(thisbroke), thisbroke))
        self.broken = True


class run_trainbot(Thread):
    def __init__(self, server, port, nick):
        self.serverspec = [(server, port)]
        self.nick = nick
        Thread.__init__(self)
        
    def run(self):
        self.bot = reloader(self.serverspec, self.nick)
        self.bot.start()
        
    def stop_bot(self):
        self.bot.disconnect()
        self.bot.connection.close()

botnicks = ["tra1n", "tra2n", "tra3n"]
for nick in botnicks:
    bot = run_trainbot("irc.freenode.net", 6667, nick)
    bot.daemon = True
    bot.start()

while True:
    time.sleep(1000)
