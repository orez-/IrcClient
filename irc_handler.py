import socket
import random
import threading
import re


# def source.nick:
#     return source.partition("!")[0][1:]

class Source(str):
    def __new__(cls, content):
        return str.__new__(cls, content)

    def __init__(self, string):
        nick, _, self.host = string.partition("!")
        self.nick = nick[1:]


class UserData(object):
    def __init__(self, nick):
        self.nick = nick
        self.ip = None
        self.name = None
        self.hostname = None
        self.ACCd = False

    def __str__(self):
        return str(self.__dict__)


class UserList(object):
    def __init__(self):
        self.users = dict()

    def add(self, user):
        if user not in self.users:
            self.users[user] = UserData(user)
            return True
        return False


class IrcListener(object):
    def on_recv_join(self, source, _, channel):
        pass

    def on_recv_part(self, source, _, channel, *reason):
        pass

    def on_recv_notice(self, source, NOTICE, _, *message):
        pass

    def on_recv_privmsg(self, source, _, target, *message):
        pass

    def on_recv_quit(self, source, _, *reason):
        pass

    def on_recv_nick(self, source, _, new_nick):
        pass

    def on_recv_end_of_whois(self, *_):
        pass

    def on_recv_whois_response_311(self, *_):
        # whois response: source 311 NICK user_nick hname[@] host * :Realname
        pass

    def on_recv_intro_blurb(self, *_):
        pass

    def on_recv_whois_response_378(self, *_):
        # whois response: source 378 NICK user_nick :is connecting from *@host ip
        pass

    def on_recv_initial_names(self, *_):
        pass

    def on_recv_join_topic(self, source, _, my_nick, channel, *topic):
        pass

    def on_recv_chan_forward(self, source, _, my_nick, channel, redirect, *message):
        pass

    def on_recv_dummy(self, source, id, *rest):
        print source, id, ' '.join(rest)

    def on_recv_mode(self, source, _, nick, *flags):
        pass


class IrcCLIListener(IrcListener):
    def on_recv_join(self, source, _, channel):
        print source.nick, "has joined", channel

    def on_recv_part(self, source, _, channel, *reason):
        reason = ' '.join(reason)
        print source.nick, "has parted from", channel, reason

    def on_recv_notice(self, source, NOTICE, _, *message):
        message = ' '.join(message)[1:]
        print ''.join(("!", source.nick, "! ", message))        

    def on_recv_privmsg(self, source, _, target, *message):
        message = ' '.join(message)[1:]
        nick = source.nick
        if message.startswith("\x01ACTION "):
            print "*" + nick, message[8:-1]
        else:
            print ''.join(("<", nick, "> ", message))
            if message == "die":
                raise

    def on_recv_quit(self, source, _, *reason):
        reason = ' '.join(reason)
        print source.nick, "has quit", reason

    def on_recv_nick(self, source, _, new_nick):
        print source.nick, "is now known as", new_nick

    def on_recv_join_topic(self, source, _, my_nick, channel, *topic):
        topic = ' '.join(topic)

    def on_recv_mode(self, source, _, nick, *flags):
        print "  MODE", ' '.join(flags), "set on", nick


class IrcHandler(threading.Thread):
    def __init__(self, listeners=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.go = True
        self.user_list = UserList()
        self.listeners = []
        if listeners is not None:
            self.listeners = listeners

        lower = "abcdefghijklmnopqrstuvwxyz"
        chars = lower + "0123456789-_"
        self.NICK = random.choice(lower) + ''.join((random.choice(chars) for _ in xrange(15)))

        self.socket = socket.socket()

    def send_join(self, channel):
        self.send_raw("JOIN", channel)

    def send_quit(self, *reason):
        self.send_raw("QUIT :", *reason, separator="")

    def send_nick(self, nick):
        self.send_raw("NICK", nick)

    def send_raw(self, *args, **kwargs):
        sep = " "
        if "separator" in kwargs:
            sep = kwargs["separator"]
        self.socket.send(sep.join(map(str, args)) + "\r\n")

    def send_privmsg(self, target, message):
        self.send_raw("PRIVMSG", target, ":" + message)

    def send_me(self, target, message):
        self.send_privmsg(target, "\x01ACTION" + message + "\x01")

    def stop(self):
        self.go = False

    def handle_line(self, line):
        words = line.split(" ")
        if words[0] == "PING":
            self.send_raw("PONG", words[1])
        else:
            if words[1] in IrcHandler.incoming_commands:
                words = [Source(words[0])] + words[1:]
                for listener in self.listeners:
                    IrcHandler.incoming_commands[words[1]](listener, words)
            else:
                print "!! ", words

    def run(self):
        print "Please wait... connecting to server..."
        s = self.socket

        HOST = "irc.freenode.net"
        PORT = 6667
        IDENT = self.NICK
        REALNAME = "Zoosmell Pooplord"

        s.connect((HOST, PORT))
        self.send_raw("NICK", self.NICK)
        self.send_raw("USER", IDENT, "0 *", ":" + REALNAME)
        self.send_raw("JOIN :##f8d66302547ac2672f30864f1f3e0b7a")

        readbuffer = ""
        while self.go:
            readbuffer += s.recv(1024)
            temp = readbuffer.split("\n")  # split by messages
            readbuffer = temp.pop()  # the last one is still receiving

            for line in temp:
                line = line.rstrip()
                self.handle_line(line)

    incoming_commands = {
        "PRIVMSG": lambda w, a: w.on_recv_privmsg(*a),
        "NOTICE": lambda w, a: w.on_recv_notice(*a),
        "JOIN": lambda w, a: w.on_recv_join(*a),
        "NICK": lambda w, a: w.on_recv_nick(*a),
        "PART": lambda w, a: w.on_recv_part(*a),
        "QUIT": lambda w, a: w.on_recv_quit(*a),
        "MODE": lambda w, a: w.on_recv_mode(*a),
        "001": lambda w, a: w.on_recv_dummy(*a),
        "002": lambda w, a: w.on_recv_dummy(*a),
        "003": lambda w, a: w.on_recv_dummy(*a),
        "004": lambda w, a: w.on_recv_dummy(*a),
        "005": lambda w, a: w.on_recv_dummy(*a),
        "250": lambda w, a: w.on_recv_dummy(*a),
        "251": lambda w, a: w.on_recv_dummy(*a),
        "252": lambda w, a: w.on_recv_dummy(*a),
        "253": lambda w, a: w.on_recv_dummy(*a),
        "254": lambda w, a: w.on_recv_dummy(*a),
        "255": lambda w, a: w.on_recv_dummy(*a),
        "265": lambda w, a: w.on_recv_dummy(*a),
        "266": lambda w, a: w.on_recv_dummy(*a),
        "311": lambda w, a: w.on_recv_whois_response_311(*a),
        "318": lambda w, a: w.on_recv_end_of_whois(*a),
        "332": lambda w, a: w.on_recv_join_topic(*a),
        "353": lambda w, a: w.on_recv_initial_names(*a),
        "366": lambda w, a: w.on_recv_dummy(*a),
        "372": lambda w, a: w.on_recv_intro_blurb(*a),
        "375": lambda w, a: w.on_recv_dummy(*a),
        "376": lambda w, a: w.on_recv_dummy(*a),
        "378": lambda w, a: w.on_recv_whois_response_378(*a),
        "470": lambda w, a: w.on_recv_chan_forward(*a),
    }


if __name__ == "__main__":
    i = IrcHandler([IrcCLIListener()])
    i.run()
