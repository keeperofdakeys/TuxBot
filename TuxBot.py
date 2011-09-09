from irc import IrcClient
from configfile import ConfigFile
import xkcd
import man
import re
import sys
import time
import random
import os
import exceptions

server = "irc.esper.net"
port = 6667
channel = "#Linux"
nick = "TuxBot"
realname = "The #Linux Bot, development version"
quitmessage = "Segmentation fault"
config = ConfigFile(os.environ["HOME"] + "/tuxbotfile")

commandref='''!help <key> -- get help about <key>
!man <section> <name> -- get the URL to an online man page
!synopsis <section> <name> -- get the SYNOPSIS section of the specified man page
!man <criteria> -- search for an online man page
!xkcd -- get a link to a random xkcd comic
!xkcd <number> -- get the link to the specified xkcd
!xkcd-linux -- get a random xkcd comic that mentions Linux
(Note: you can use "geek" instead of "linux" in the above command for geeky comics)
!time -- show the current time
!time <strftime> -- show the current time, with custom formatting. See "man strftime" for more.
(Note: you can use "date" instead of "time" in the above two commands)
!quit -- make TuxBot quit'''

def clean_string(string):
    s = re.sub("[^-_\w\s]", "", string.lower())
    s = re.sub("\s+", " ", s)
    print "Cleaned String: " + s
    return s

def process_message(line, sender):
    line = line.strip()
    if len(line) == 0:
        return

    if line[0] == "!":

        # !help -- get help about TuxBot's commads
        match = re.match(r'!help$', line)
        if match:
            irc.send_private_notice(commandref, sender)
            return

        # !help <key> -- get help
        match = re.match(r'!help\s+(.*)$', line)
        if match:
            key = clean_string(match.group(1))
            text = config.get_help(key)
            if text:
                irc.send_message("%s" % (text))
            else:
                irc.send_message("I don't have an answer for \"%s\". You can set it using the \"!sethelp question: answer\" command." % (key))
            return

        # !man <section> <name> -- get the URL to an online man page
        match = re.match(r'!man\s+(\w+)\s+([-A-Za-z0-9_]+)$', line)
        if match:
            irc.send_message(man.get(match.group(1), match.group(2)))
            return
        # !synopsis <section> <name> -- print the "SYNOPSIS" section of the specified man page
        match = re.match(r'!synopsis\s+(\w+)\s+(\w+)$', line)
        if match:
            text = man.synopsis(match.group(1), match.group(2))
            if not text:
                irc.send_message("Failed to get man page for \"%s\" in section \"%s\"" % (match.group(2), match.group(1)))
                return
            irc.send_message(text)
            return
        # !man <criteria> -- search for an online man page
        match = re.match(r'!man\s+(\w+)$', line)
        if match:
            irc.send_message(man.search(match.group(1)))
            return

        # !xkcd -- get a random xkcd comic
        match = re.match(r'!xkcd$', line)
        if match:
            irc.send_message(xkcd.get_random())
            return
        # !xkcd <index> -- get an xkcd comic by index
        match = re.match(r'!xkcd\s+([0-9]+)$', line)
        if match:
            irc.send_message(xkcd.get_url(int(match.group(1))))
            return

        # !xkcd-linux and !xkcd-geek -- get linux-related and geeky xkcd comics
        match = re.match(r'!xkcd-linux$', line)
        if match:
            l = config.get_linux_xkcds()
            if not l:
                irc.send_message("No linux-related comics in list.")
            else:
                irc.send_message(xkcd.get_url(int(l[random.randint(0, len(l)-1)])))
            return
        match = re.match(r'!xkcd-geek$', line)
        if match:
            l = config.get_geek_xkcds()
            if not l:
                irc.send_message("No linux-related comics in list.")
            else:
                irc.send_message(xkcd.get_url(int(l[random.randint(0, len(l)-1)])))
            return

        # !wikipedia -- get a random wikipedia article
        match = re.match(r'!wikipedia$', line)
        if match:
            irc.send_message("http://en.wikipedia.org/wiki/Special:Random")
            return
        # !wikipedia <article> -- get a link to wikipedia article
        match = re.match(r'!wikipedia\s+([^\s].+)$', line)
        if match:
            irc.send_message("http://en.wikipedia.org/wiki/Special:Search?search=" + clean_string(match.group(1)).replace(" ", "+"))
            return
        # !wikipedia-<lang> -- get a random wikipedia article in a certain language
        match = re.match(r'!wikipedia-(\w+)$', line)
        if match:
            irc.send_message("http://"+match.group(1)+".wikipedia.org/wiki/Special:Random")
            return
        # !wikipedia-<lang> <article> -- get a link to wikipedia article in a certain language
        match = re.match(r'!wikipedia-(\w+)\s+([^\s].+)$', line)
        if match:
            irc.send_message("http://"+match.group(1)+".wikipedia.org/wiki/Special:Search?search=" + clean_string(match.group(2)).replace(" ", "+"))
            return

        # !time and !date -- get the current time
        match = re.match(r'!(time|date)$', line)
        if match:
            irc.send_message(time.strftime("%A %Y-%m-%d %H:%M:%S %Z"))
            return
        match = re.match(r'!(time|date)\s+([^\s].*)$', line)
        if match:
            irc.send_message(time.strftime(match.group(2)))
            return

        # !quit -- make TuxBot quit
        match = re.match(r'!quit$', line)
        if match:
            irc.quit(quitmessage)
            sys.exit(0)
            return

        irc.send_message("Invalid command.")

    else:

        response = config.get_response(clean_string(line))
        if response:
            irc.send_message(response.replace("\\s", sender))
            return

channel_ops = []
channel_voices = []

def process_mode(modeset):
    if modeset.mode is "o" and modeset.given:
        channel_ops.append(modeset.nick)
    elif modeset.mode is "o" and not modeset.given:
        channel_ops.remove(modeset.nick)
    elif modeset.mode is "v" and modeset.given:
        channel_voices.append(modeset.nick)
    elif modeset.mode is "v" and not modeset.given:
        channel_voices.remove(modeset.nick)
    #print modeset
    #setter, to, mode, given[, nick]

def process_kick(kicker, channel, nick, comment):
    try:
        channel_ops.remove(nick)
    except Error:
        pass

    try:
        channel_voices.remove(nick)
    except Error:
        pass

def process_quit(nick, comment):
    try:
        channel_ops.remove(nick)
    except Error:
        pass

    try:
        channel_voices.remove(nick)
    except Error:
        pass

def process_part(nick, channel):
    try:
        channel_ops.remove(nick)
    except Error:
        pass

    try:
        channel_voices.remove(nick)
    except Error:
        pass

irc = IrcClient(server, port, nick, realname)
joined = False

# I temporarily removed this becuase it makes it so that exceptions caused by
# bugs aren't shown.
'''old_excepthook = sys.excepthook
def new_hook(type, value, traceback):
    if type == exceptions.KeyboardInterrupt:
        irc.quit(quitmessage)
        old_excepthook(type, value, traceback)
sys.excepthook = new_hook'''

while True:
    line = irc.readline()
    if line is "" or line is None:
        continue
    print line

    # respond to PING commands
    tmp = irc.is_ping(line)
    if tmp:
        irc.send_pong(tmp)
        continue

    if not joined and line == ":"+nick+" MODE "+nick+" :+i":
        irc.join(channel)
        joined = True

    if not joined:
        continue

    # respond to posts on the channel
    tmp = irc.is_message(line)
    if tmp and tmp[1] == channel:
        process_message(tmp[2], tmp[0])
        
    tmp = irc.is_quit(line)
    if tmp is not None:
        process_quit(tmp[0], tmp[1])

    tmp = irc.is_kick(line)
    if tmp is not None:
        process_kick(tmp[0], tmp[1], tmp[2], tmp[3])

    tmp = irc.is_part(line)
    if tmp is not None:
        for channel in tmp[1]:
            process_part(tmp[0], channel)

    tmp = irc.is_mode(line)
    if tmp is not None:
        for i in tmp:
            process_mode(i)
