#! /usr//bin/python3

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
sufficientlydry = 0.0004

measurementPin = 24
chargePin = 23

# yeah it's global state fight me irl
begintime = 0
rollingAvg = 0
divisor = 0
    
class LeetBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, "hippo")], nickname, nickname)
        self.channel = channel

        self.report_interval = 28800 #8 hours
        self.scan_interval = 3600 #1 hour
        s = self.reactor.scheduler
        s.execute_every( self.scan_interval, self.startscan )
        s.execute_every( self.report_interval, self.reportdata )
        GPIO.add_event_callback( measurementPin, callback=lambda x: self.edge_callback() )

    # overrides        
    def start(self):
        """Start the bot."""
        try:
            server = self.servers.peek()
            self.connect(
                server.host,
                server.port,
                self._nickname,
                server.password,
                ircname=self._realname,
            )
            
        except irc.client.ServerConnectionError:
            sys.exit(69) # ladies...

        irc.client.SimpleIRCClient.start(self)
                
    def reportdata(self):
        global divisor
        global rollingAvg

        if divisor <= 1:
            divisor = 1
            
        avg = rollingAvg / divisor
        #logging.info("gardener: {timestamp} -- {avg}".format( timestamp=time.asctime(), avg=avg ))
        self.connection.privmsg( self.channel, "Average: {avg}".format(avg=avg) )

        if avg < sufficientlydry:
            self.alert( avg )
        
        rollingAvg = 0
        divisor = 0

    def take_snapshot(self):
        global begintime
        global divisor
        global rollingAvg
        
        if begintime != 0:
            self.connection.privmsg( self.channel, "A scan is currently running, try again in a few seconds." )
        elif divisor == 0:
            self.connection.privmsg( self.channel, "A scan has not been run since the last report.  I have initiated a scan, try again shortly." )
            self.startscan()
        else:
            current = rollingAvg / divisor
            self.connection.privmsg( self.channel, "Current rolling average sits at {avg}".format( avg = current ) )
            
    def alert(self, value):
        #logging.info("gardener: alerting based on detected value = {reading}".format( reading=value ) )
        self.connection.privmsg( self.channel, "nathan: Sensor reading below threshold ({reading})!".format(reading=value) )
        
    def startscan(self):
        global begintime
        begintime = time.clock_gettime(time.CLOCK_MONOTONIC)
        GPIO.output( chargePin, GPIO.HIGH ) #commence charge, callback will fire when it hits 2 volts

    def edge_callback(self):
        global begintime
        global rollingAvg
        global divisor

        #there seems to be a hardware-level bug where edges are spuriously detected, so:
        if begintime == 0:
            return

        # reason this works is that we shouldn't see any rising edges until startscan() gets called
        # and startscan() is responsible for setting begintime != 0
        #
        # therefore spurious events will see begintime == 0 and we can ignore.
        
        t = time.clock_gettime(time.CLOCK_MONOTONIC) - begintime
        GPIO.output( chargePin, GPIO.LOW ) #reset it for the next run
        begintime = 0
        rollingAvg += t
        divisor += 1     
        
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

        #c.privmsg( self.channel, "Commands are disabled")
        
        if cmd == "snapshot":
            self.take_snapshot()
        elif cmd == "setlevel":
            try:
                tmp = float(e.arguments[2])
                global sufficientlydry
                sufficientlydry = tmp
                c.privmsg( self.channel, "ok I have set lower threshold to {v}".format(v=sufficientlydry) )
            except:
                c.privmsg( self.channel, "Invalid argument" )
        else:
            c.privmsg( self.channel, "Invalid command" )
            
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
#   GPIO23              GPIO24                         GND
#     |                   |                             |
#     +-----[47kOhm]------+---------| capacitor  |------+
#
# and you want to measure when the voltage drop across the resistor is 0 because that means
# that your capacitor is charged.  Capacitors in this configuration obey the equation V(t) = V0 * (1 - e^[-t/tau]) where tau is the "RC constant"
#
# Conveniently, for a charging capacitor, 1 - e^-1 = 0.632 or 63.2% and it just so happens that 63.2% of 3V3 CMOS logic is 2.08V which loosely corresponds
# to the minimum input voltage to be considered a "high" which is 2 volts.
#
# not that it really matters because it's a proxy measurement anyways.

def main():
    logging.info("gardener: Raspi Gardener version 1.3.3.7 initializing...")
    GPIO.setwarnings( False )
    #GPIO.cleanup()
    GPIO.setmode( GPIO.BCM ) #so-called "broadcom numbering" which is logical numbering not physical pins

    GPIO.setup( chargePin, GPIO.OUT )
    GPIO.setup( measurementPin, GPIO.IN )
    GPIO.output( chargePin, GPIO.LOW )
    GPIO.add_event_detect( measurementPin, GPIO.RISING )
    
    bot = LeetBot("#bots", "raspi3", "irc.squishynet.net", 6667)
    logging.info("gardener: Initialization complete.  Connecting to IRC.")
    bot.start()


if __name__ == "__main__":
    main()
