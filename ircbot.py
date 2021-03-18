#! /usr/local/bin/python3

import sys
import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr

class LeetBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, "hippo")], nickname, nickname)
        self.channel = channel

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

        c.privmsg("Commands are disabled")
        
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

def main():
    bot = LeetBot("#bots", "raspi3bplus", "irc.squishynet.net", 6667)
    bot.start()


if __name__ == "__main__":
    main()
