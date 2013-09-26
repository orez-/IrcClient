from _tkinter import TclError
import Tkinter as tk
from ScrolledText import ScrolledText
from idlelib.WidgetRedirector import WidgetRedirector

from irc_handler import IrcHandler, IrcListener


class ReadOnlyText(ScrolledText):
    def __init__(self, *args, **kwargs):
        ScrolledText.__init__(self, *args, **kwargs)
        self.redirector = WidgetRedirector(self)
        self.insert = self.redirector.register("insert", lambda *args, **kw: "break")
        self.delete = self.redirector.register("delete", lambda *args, **kw: "break")
        self.config(wrap=tk.WORD)


def send(frame, client):
    def anon(event):
        irc = client.irc
        message = frame.inputbox.get()
        frame.inputbox.delete(0, tk.END)
        if message.startswith("/"):
            command, _, rest = message.partition(" ")
            command = command[1:].lower()
            if command == "me":
                message = ''.join(("\x01ACTION ", message[4:], "\x01"))
            elif command == "join":
                if rest != "0":
                    irc.send_join(rest)
                return
            elif command == "quit":
                irc.send_quit(rest)
                return
            elif command == "nick":
                irc.send_nick(rest)
                return
            else:
                client.add_raw("Unknown command /" + command)
                return
        if frame.name != "Status":
            client.add_message(irc.NICK, message)
            irc.send_privmsg(frame.name, message)
    return anon

class ClientListener(IrcListener):
    def __init__(self, client):
        IrcListener.__init__(self)
        self.client = client

    def on_recv_privmsg(self, source, _, target, *message):
        message = ' '.join(message)[1:]
        frame = self.client.channel_list.get_frame(target)
        frame.add_message(source.nick, message)

    def on_recv_notice(self, source, _, target, *message):
        message = ' '.join(message)[1:]
        self.client.add_notice(source.nick, message)

    def on_recv_join(self, source, _, channel):
        self.client.channel_list.add_channel(channel)

    def on_recv_nick(self, source, _, new_nick):
        # TODO: needs better aim
        new_nick = new_nick[1:]
        if source.nick == self.client.irc.NICK:
            self.client.irc.NICK = new_nick
        self.client.add_raw(' '.join((source.nick, "is now known as", new_nick, "\n")))


class ChannelList(tk.Frame):
    def __init__(self, master, client):
        tk.Frame.__init__(self, master)
        self.client = client
        self.master = master
        self.channel_buttons = []

    def add_channel(self, name):
        f = ChannelFrame(self.master, self.client, name)
        b = tk.Button(self, text=name, command=self.client.swap(f))
        self.channel_buttons.append((name, b, f))
        b.pack(side=tk.LEFT)

    def get_frame(self, target):
        for name, _, f in self.channel_buttons:
            if name == target:
                return f
        return None


class ChannelFrame(tk.Frame):
    def __init__(self, master, client, name):
        tk.Frame.__init__(self, master)
        self.name = name
        self.chatbox = ReadOnlyText(self)
        self.chatbox.grid(row=1, column=0)
        self.userlist = tk.Listbox(self)
        self.userlist.grid(row=1, column=1)
        self.inputbox = tk.Entry(width=90)
        self.inputbox.bind("<Return>", send(self, client))
        self.inputbox.grid(row=2, column=0, columnspan=2)

    def add_raw(self, message):
        self.chatbox.insert(tk.END, message)

    def add_message(self, user, message):
        if message.startswith("\x01ACTION "):
            message = ''.join(("*", user, message[7:-1], "\n"))
        else:
            message = ''.join(("<", user, "> ", message, "\n"))
        self.add_raw(message)

    def add_notice(self, user, message):
        message = ''.join(("!", user, "! ", message, "\n"))
        self.add_raw(message)


class IrcClient(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        master.title("IRC")
        self.channel_list = ChannelList(master, self)
        self.channel_list.grid(row=0, column=0)
        self.channel_frame = ChannelFrame(master, self, "Status")
        self.channel_frame.grid(row=1, column=0)

        self.irc = IrcHandler([ClientListener(self)])
        self.irc.start()

    def swap(self, frame):
        def anon():
            self.channel_frame.grid_forget()
            self.channel_frame = frame
            self.channel_frame.grid(row=1, column=0)
        return anon

    def add_raw(self, message):
        self.channel_frame.add_raw(message)

    def add_message(self, user, message):
        self.channel_frame.add_message(user, message)

    def add_notice(self, user, message):
        self.channel_frame.add_notice(user, message)


if __name__ == "__main__":
    root = tk.Tk()
    app = IrcClient(master=root)
    app.mainloop()
    try:
        root.destroy()
    except TclError:
        pass
