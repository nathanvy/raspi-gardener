#! /usr/local/bin/python3

import sys
import irc.bot
import irc.strings
import tempora
import numpy
import time
import logging
import RPi.GPIO as GPIO
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr

#these are in seconds as a proxy for the time constant tau
sufficientlywet = 0.005
sufficientlydry = 0.001

measurementPin = 24
chargePin = 23

begintime = 0
    
class LeetBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, "hippo")], nickname, nickname)
        self.channel = channel

        self.scan_interval = 60 #seconds
        s = self.reactor.scheduler
        s.execute_every( self.scan_interval, self.startscan )

        GPIO.add_event_callback( measurementPin, callback=lambda x: self.edge_callback() )

    #where the sausage gets made
    def startscan(self):
        global begintime
        begintime = time.clock_gettime(time.CLOCK_MONOTONIC)
        GPIO.output( chargePin, GPIO.HIGH ) #commence charge, callback will fire when it hits 2 volts

    def edge_callback(self):
        global begintime
        t = time.clock_gettime(time.CLOCK_MONOTONIC)
        GPIO.output( chargePin, GPIO.LOW ) #reset it for the next run
        self.connection.privmsg( self.channel, "I measured {first} and {second} for t2 - t1 = {ans}".format(first=t, second=begintime, ans=t-begintime ))
        begintime = 0        
        
    def on_nicknameinuse( self, c, e ):
        c.nick(c.get_nickname() + "_")

    def on_welcome( self, c, e ):
        c.join(self.channel)

    def on_privmsg( self, c, e ):
        self.do_command( e, e.arguments[0])

    def on_pubmsg( self, c, e ):
        a = e.arguments[0].split( ":", 1 )
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    # stolen from some random github example
    def do_command(self, e, cmd):
        nick = e.source.nick
        c = self.connection

        c.privmsg( self.channel, "Commands are disabled")
        
        # if cmd == "disconnect":
        #     self.disconnect()
        # elif cmd == "die":
        #     self.die()
        # elif cmd == "stats":
        #     for chname, chobj in self.channels.items():
        #         c.notice(nick, "--- Channel statistics ---")
        #         c.notice(nick, "Channel: " + chname)
        #         users = sorted(chobj.users())
        #         c.notice(nick, "Users: " + ", ".join(users))
        #         opers = sorted(chobj.opers())
        #         c.notice(nick, "Opers: " + ", ".join(opers))
        #         voiced = sorted(chobj.voiced())
        #         c.notice(nick, "Voiced: " + ", ".join(voiced))
        # elif cmd == "dcc":
        #     dcc = self.dcc_listen()
        #     c.ctcp(
        #         "DCC",
        #         nick,
        #         "CHAT chat %s %d"
        #         % (ip_quad_to_numstr(dcc.localaddress), dcc.localport),
        #     )
        # else:
        #     c.notice(nick, "Not understood: " + cmd)



# so you have something like
#   GPIO23                      GPIO24                                        GND
#     |                                        |                                                   |
#     +-----[47kOhm]------+---------| capacitor  |------+
#
# and you want to measure when the voltage drop across the resistor is 0 because that means
# that your capacitor is charged.  Capacitors in this configuration obey the equation V(t) = V0 * (1 - e^[-t/tau]) where tau is the "RC constant"
#
# Conveniently, for a charging capacitor, 1 - e^-1 = 0.632 or 63.2% and it just so happens that 63.2% of 3V3 CMOS logic is 2.08V which loosely corresponds
# to the minimum input voltage to be considered a "high" which is 2 volts.

def main():
    print("Raspi Gardener version 1.3.3.7 initializing...")
    #GPIO.setwarnings( False )
    GPIO.setmode( GPIO.BCM ) #so-called "broadcom numbering" which is logical numbering not physical pins

    GPIO.setup( chargePin, GPIO.OUT)
    GPIO.setup( measurementPin, GPIO.IN )
    GPIO.output( chargePin, GPIO.LOW )
    GPIO.add_event_detect( measurementPin, GPIO.RISING )
    
    bot = LeetBot("#bots", "raspi3bplus", "irc.squishynet.net", 6667)
    print("Initialization complete.  Connecting to IRC.")
    bot.start()


if __name__ == "__main__":
    main()
