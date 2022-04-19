# by lexande and contributors - BSD licensed
#!/usr/bin/env python

import codecs
import irc.bot
import re
import mechanize
import time
import urllib
import asciis
from importlib import reload
from trainbotpass import ownernick, botnicks

class trainbot(object):
    def __init__(self):
        reload(asciis)
        self.lastdraw = 0

    def dontflood(self):
        if time.time() - self.lastdraw < 1:
            time.sleep(1)
        else:
            self.lastdraw = time.time()

    def on_pubmsg(self, c, event):
        pass

    def on_privmsg(self, c, event):
        pass


class tra1nbot(trainbot):
    def amsearch(self, c, name, channel, query):
        match = re.match("!amtrak (.*) to (.*) on (.*)", query)
        try:
            trips = self.amscrape(match.group(1), match.group(2), match.group(3))
        except Exception as inst:
            c.privmsg(channel, "amtrak search failed")
            print("amtrak oops: ", str(inst))
            return
        if trips:
            c.privmsg(channel, "depart    duration     arrive     price")
            for trip in trips:
                time.sleep(0.2)
                c.privmsg(channel, trip)
        else:
            c.privmsg(channel, "no trains found :(")

    def mbsearch(self, c, name, channel, query):

        match = re.match("!megabus (.*) to (.*) on (.*)", query)

        try:
            trips = self.mbscrape(match.group(1), match.group(2), match.group(3))

        except Exception as inst:
            c.privmsg(channel, "megabus search failed")
            print("megabus oops: ", str(inst))
            return
        if trips:
            c.privmsg(channel, "depart    arrive    price")
            for trip in trips:
                time.sleep(0.2)
                c.privmsg(channel, trip)
        else:
            c.privmsg(channel, "no busses found :(")

    def amscrape(self, orig, dest, date):
        splitdate = date.split("-")
        url = "http://tickets.amtrak.com/itd/amtrak/FareFinder?"
        get_options = {'_tripType': 'OneWay',
                       '_origin': re.sub(" ", "%20", orig),
                       '_depmonthyear': "-".join((splitdate[0], splitdate[1])),
                       '_depday': splitdate[2],
                       '_destination': re.sub(" ", "%20", dest),
                       '_adults': '1'}
        response = mechanize.urlopen(url + urllib.urlencode(get_options))
        html = response.read()
        lines = html.split("onAddToCartClick")
        trips = []
        for line in lines:
            result = ""
            matches = re.findall("Departs: (..?):(..) (.M)", line)
            if matches:
                result += "%s    " % self.timeformat(int(matches[0][0]), int(matches[0][1]), matches[0][2])
            match = re.search('_duration_span" style="display:none">..([0-9HM]*)</span>', line)
            if match:
                dur = match.group(1)
                if not re.search("H", dur):
                    dur = "0H" + dur
                if not re.search("M", dur):
                    dur = dur + "0M"
                dmatch = re.search("([0-9]*)H([0-9]*)M", dur)
                result += "%3ih%02im       " % (int(dmatch.group(1)), int(dmatch.group(2)))
            matches = re.findall("Arrives: (..?):(..) (.M)", line)
            if matches:
                result += "%s      " % self.timeformat(int(matches[-1][0]), int(matches[-1][1]), matches[-1][2])
            match = re.search('CartPrice">\$([0-9]*).00<', line)
            if match:
                result += "$%3i.00" % int(match.groups(1)[0])
            if result != "":
                trips.append(result)
        return trips

    def mbscrape(self, orig, dest, date):
        orig = orig.lower()
        dest = dest.lower()
        splitdate = date.split("-")
        datestring = "%s/%s/%s" % (splitdate[1], splitdate[2], splitdate[0])
        br = mechanize.Browser()
        br.set_handle_robots(False)  # no robots
        br.set_handle_refresh(False)  # can sometimes hang without this
        br.addheaders = [('User-agent', 'Lynx/2.8.7pre.5 libwww-FM/2.14 SSL-MM/1.4.1')]
        br.open("http://mobile.usablenet.com/mt/us.megabus.com/Default.aspx?un_jtt_v_search=on")
        br.form = list(br.forms())[0]
        control = br.form.find_control("JourneyPlanner$ddlOrigin")
        keys = []
        values = []
        for item in control.items:
            keys.append(item.name)
            for label in item.get_labels():
                values.append(str(label.text)[:-4].lower())
        cities = dict(zip(values, keys))
        for control in br.form.controls:
            if control.name == "JourneyPlanner$ddlOrigin":
                control.value = [cities[orig]]
                br.submit('un_jtt_searchform_origin')
        br.form = list(br.forms())[0]
        for control in br.form.controls:
            if control.name == "JourneyPlanner$ddlDest":
                control.value = [cities[dest]]
                br.submit('un_jtt_searchform_destination')
        br.form = list(br.forms())[0]
        for control in br.form.controls:
            if control.name == "JourneyPlanner$txtOutboundDate":
                control.value = datestring
                response = br.submit('un_jtt_searchformSubmit')
        html = response.read()
        br.close()
        lines = re.split("Details", html)
        trips = []
        for line in lines:
            result = ""
            match = re.search("Departs</B> (..?):(..).nbsp.(.M)", line)
            if match:
                result += "%s     " % self.timeformat(int(match.group(1)), int(match.group(2)), match.group(3))
            match = re.search("Arrives</B> (..?):(..).nbsp.(.M)", line)
            if match:
                result += "%s     " % self.timeformat(int(match.group(1)), int(match.group(2)), match.group(3))
            match = re.search("Price.+?\$([0-9]*).00", line)
            if match:
                result += "$%3i.50" % int(match.groups(1)[0])
            if result != "":
                trips.append(result)
        return trips

    def timeformat(self, hour, minute, ampm):
        if hour == 12:
            hour = 0
        if ampm == "PM":
            hour += 12
        return "%02i:%02i" % (hour, minute)

    def originstory(self, c, source, channel, message):
        if re.match("!origin *$", message):
            name = source
        else:
            qmatch = re.match("!origin (.*)", message)
            name = qmatch.group(1).rstrip()
        if not re.match("^[a-zA-Z0-9_]*$", name):
            return
        try:
            f = codecs.open('origins/' + name.lower() + '.txt', 'r', 'utf-8')
            c.privmsg(channel, ''.join([name, "'", 's origin story: "', f.readline().rstrip(), '"']))
            f.close()
        except IOError:
            c.privmsg(channel,
                      name + " has not defined an origin story.  They are encouraged to do so using !setorigin.")
            return

    def setorigin(self, c, source, message):
        if not re.match("^[a-zA-Z0-9_]*$", source):
            return
        match = re.match("!setorigin (.*)", message)
        f = codecs.open('origins/' + source.lower() + '.txt', 'w', 'utf-8')
        f.write(match.group(1).rstrip())
        f.close()

    def on_pubmsg(self, c, event):
        for i in range(0, len(asciis.evilpatterns)):
            if (re.search(asciis.evilpatterns[i][0], event.arguments[0]) or
                    re.search(asciis.evilpatterns[i][0], event.source.nick)):
                self.dontflood()
                c.privmsg(event.target, "fuck you")
                c.kick(event.target, event.source.nick, "fuck %s" % (asciis.evilpatterns[i][1]))
                return
        for i in range(0, len(asciis.asciipatterns)):
            if re.search(asciis.asciipatterns[i], event.arguments[0]):
                self.dontflood()
                for line in asciis.asciis[i][0]:
                    c.privmsg(event.target, line)
                c.privmsg(botnicks[1], " ".join([str(i), event.target]))
                return
        if re.match('Good (.*), programs.', event.arguments[0]) and event.source.nick == ownernick:
            self.dontflood()
            match = re.match('Good (.*), programs.', event.arguments[0])
            c.privmsg(event.target, 'Good ' + match.group(1) + ', kernel.')
        if re.match("!megabus", event.arguments[0]):
            self.dontflood()
            self.mbsearch(c, event.source.nick, event.target, event.arguments[0])
        if re.match("!amtrak", event.arguments[0]):
            self.dontflood()
            self.amsearch(c, event.source.nick, event.target, event.arguments[0])
        if re.match("!origin", event.arguments[0]):
            self.dontflood()
            self.originstory(c, event.source.nick, event.target, event.arguments[0])
        if re.match("!setorigin ", event.arguments[0]):
            self.setorigin(c, event.source.nick, event.arguments[0])

    def on_privmsg(self, c, event):
        message = event.arguments[0].split(" ")
        if event.source.nick == ownernick and message[0] == "Join":
            c.join(message[1])
            c.privmsg(botnicks[1], event.arguments[0])
        elif event.source.nick == ownernick and message[0] == "Part":
            c.part(message[1])
            c.privmsg(botnicks[1], event.arguments[0])


class tra2nbot(trainbot):
    def on_privmsg(self, c, event):
        message = event.arguments[0].split(" ")
        if event.source.nick == botnicks[0]:
            if message[0] == "Join":
                c.join(message[1])
            elif message[0] == "Part":
                c.part(message[1])
            else:
                for line in asciis.asciis[int(message[0])][1]:
                    c.privmsg(message[1], line)
            c.privmsg(botnicks[2], event.arguments[0])


class tra3nbot(trainbot):
    def on_privmsg(self, c, event):
        message = event.arguments[0].split(" ")
        if event.source.nick == botnicks[1]:
            if message[0] == "Join":
                c.join(message[1])
            elif message[0] == "Part":
                c.part(message[1])
            else:
                for line in asciis.asciis[int(message[0])][2]:
                    c.privmsg(message[1], line)


class shuttlebusbot(trainbot):
    def on_pubmsg(self, c, event):
        for i in range(0, len(asciis.asciipatterns)):
            if re.search(asciis.asciipatterns[i], event.arguments[0]):
                self.dontflood()
                if len(asciis.asciis[i][1]) > 0:
                    c.privmsg(event.target, "Trainbot is offline for maintenance.")
                else:
                    for line in asciis.asciis[i][0]:
                        c.privmsg(event.target, line)
                return
        if re.match("!megabus", event.arguments[0]):
            self.dontflood()
            c.privmsg(event.target, "Trainbot is offline for maintenance.")
        if re.match("!amtrak", event.arguments[0]):
            self.dontflood()
            c.privmsg(event.target, "Trainbot is offline for maintenance.")

