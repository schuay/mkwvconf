#!/usr/bin/python2
# -*- coding: utf-8 -*-

import sys
import string
import os
from xml import xpath
from xml.dom.minidom import parse

class Mkwvconf:

  #########
  # file paths
  #########

  xmlPath = '/usr/share/mobile-broadband-provider-info/serviceproviders.xml'
  configPath = '/etc/wvdial.conf'
  
  #########
  # class members
  #########

  parameters = {}
  providers = {}
  countryCode = ""
  chosenProvider = ""

  introMessage = """
mkwvconf automatically generates a dialer section for use in wvdial.conf based on mobile-broadband-provider-info.

If a provider is missing from the list, add a bug at http://bugzilla.gnome.org/enter_bug.cgi?product=NetworkManager (include your provider name, your country, your plans marketing name if you know it, and of course the APN you're using for data). For more information about the mobile broadband provider database, see http://blogs.gnome.org/dcbw/2009/06/22/mobile-broadband-assistant-makes-it-easy/ .

The configuration generated by mkwvconf overwrites CID 1 with your provider info ('Init2=AT+CGDCONT=1,...') which is then called by dialing *99***1# (the digit before the trailing '#' specifies which CID to use).

Further reading on APNs can be found here: http://mail.gnome.org/archives/networkmanager-list/2008-August/msg00191.html. Thanks goes to Antti Kaijanmäki for explanations and links!"""

  #########
  # class methods
  #########

  def __init__(self):
    self.doc = parse(self.xmlPath)

  def displayIntro(self):
    os.system('clear')
    print self.introMessage

  def getCountryCodes(self):
    """returns a list of all country codes"""
    return [ str(n.value) for n in self.getNodesFromXml("country/@code") ]


  def selectCountryCode(self):
    """lets user choose a country code and returns the chosen value"""

    l = self.getCountryCodes()

    print "\nAvailable country codes:\n"
    print l

    country = ""

    while country not in l:
        country = raw_input("\nGet providers for which country code? : ")

    return country

  def getNodesFromXml(self, xquery):
    """returns results of xquery as a list"""
    return xpath.Evaluate(xquery, self.doc.documentElement)

  def getProviders(self):
    """fills dictionary of providers for the specified country code with entries containing {index: providername}"""
    nodes = self.getNodesFromXml('country[@code=\'' + self.countryCode +  '\']/provider/name')
    providernames = [ n.firstChild.nodeValue for n in nodes ]
    indices = range(len(providernames))
    self.providers = dict(zip(indices, providernames))

  def chooseProvider(self):
    """lets user choose a provider and sets self.chosenProvider to the providername"""
    max = len(self.providers) - 1
    os.system('clear')
    print "\nProviders for '" + self.countryCode + "':\n"
    for k, v in self.providers.items():
        print str(k) + ": " + v

    input = -1

    while input > max or input < 0:
        inputStr = self.getUserInput("Choose a provider [0-" + str(max) + "]:")
        try:
            input = string.atoi(inputStr)
            if input < 0 or input > max:
                print "Input needs to be between 0 and " + str(max)
        except:
            input = -1
            print "Input needs to be an integer."

    self.chosenProvider = self.providers[int(input)]

  def selectApn(self, node):
      """takes a provider node, lets user select one apn (if several exist) and returns the chosen node"""
      apnNode = node.getElementsByTagName("apn")[0]
      apn = apnNode.getAttribute("value")
      self.parameters["apn"] = apn

      apns = node.getElementsByTagName("apn")
      apnnames = [ n.getAttribute("value") for n in apns ]

      apncount = len(apns)
      if apncount == 1:
          return apns[0]

      print "Available APNs:\n"
      for k, v in zip(range(apncount), apnnames):
          print str(k) + ": " + v

      input = -1
      max = apncount - 1
      while input > max or input < 0:
          inputStr = self.getUserInput("Choose an APN [0-" + str(max) + "]:")
          try:
              input = string.atoi(inputStr)
              if input < 0 or input > max:
                  print "Input needs to be between 0 and " + str(max)
          except:
              input = -1
              print "Input needs to be an integer."

      return apns[int(input)]

  def makeConfig(self):
    """get final information from user and assembles configuration section. the configuration is either written to wvdial.conf or printed for manual insertion"""
    nodes = self.getNodesFromXml("country[@code='" + self.countryCode +  "']/provider[name='" + self.chosenProvider + "']")
    apn = self.selectApn(nodes[0])
    self.parseProviderNode(apn)

    self.parameters["modem"] = self.getModemDevice()
    self.parameters["profileName"] = self.getUserInput("Enter name for configuration: ","DefaultProfile")

    editConf = raw_input("\nDo you want me to try to modify " + self.configPath + " (you will need superuser rights)? Y/n: ")
    os.system('clear')
    if editConf in ["", "Y",  "y"]:
        self.writeConfig()
    else:
        print "\n\nDone. Insert the following into " + self.configPath + " and run 'wvdial " + self.parameters["profileName"] + "' to start the connection.\n\n"
        print self.formatConfig()

  def writeConfig(self):    
    """append or replace the configuration section to wvdial.conf"""
    if not os.path.exists(self.configPath):
        print "\nWarning: " + self.configPath + " doesn't exist, creating new file."
        f = open(self.configPath, 'w')
        f.close()

    f = open(self.configPath, 'r')
    text = f.read()
    f.close()

    snippetStart = text.find("[Dialer %(profileName)s]" % self.parameters)
    if snippetStart != -1:
        snippetEnd = text.find("[Dialer ", snippetStart+1)
        print "\nThe following part of wvdial.conf will be replaced: \n\n" + text[snippetStart:snippetEnd]
        print "by: \n\n" + self.formatConfig()
        text = text.replace(text[snippetStart:snippetEnd], self.formatConfig())
    else:
        print "\nThe following will be appended to wvdial.conf: \n\n" + self.formatConfig()
        text += "\n" + self.formatConfig()

    editConf = raw_input("Write to file? Y/n: ")
    if editConf in ["", "Y",  "y"]:
        f = open(self.configPath, 'w')
        f.write(text)
        f.close()

        print "wvdial.conf edited successfully, run 'wvdial " + self.parameters["profileName"] + "' to start the connection.\n\n"

  def formatConfig(self):
    """formats the information contained in parameters into a valid wvdial.conf format"""

    if not 'usr' in self.parameters:
        self.parameters['usr'] = ""

    if not 'pw' in self.parameters:
        self.parameters['pw'] = ""

    return \
"""[Dialer %(profileName)s]
Modem Type = Analog Modem
Phone = *99***1#
ISDN = 0
Baud = 460800
Username = %(usr)s
Password = %(pw)s
Modem = %(modem)s
Init1 = ATZ
Init2 = at+cgdcont=1,"ip","%(apn)s"
Stupid Mode = 1
""" % self.parameters

  def getModemDevice(self):
    """return modem location provided by user"""
    defaultLocation = "/dev/ttyUSB0"
    input = "initialValue"

    while not input.startswith("/dev/") or len(input) == 0:
        input = self.getUserInput("Enter modem location (default is /dev/ttyUSB0): ",  defaultLocation)

    if len(input.strip()) == 0:
        input = defaultLocation

    return input

  def getUserInput(self, prompt, default=""):
    """utility method for getting user input. displays prompt, optional default fallback"""
    accept = "n"
    inp = ""
    while accept == "n" or accept == "N":
        inp = raw_input("\n" + prompt)
        if len(inp.strip()) == 0:
            inp = default
        accept = raw_input("Your choice: '" + inp + "'. Is this correct? Y/n: ")
    return inp

  def parseProviderNode(self, apnNode):
    """fill parameter dictionary from provider xml node"""
    self.parameters = {}

    apn = apnNode.getAttribute("value")
    self.parameters["apn"] = apn

    usrNodes = apnNode.getElementsByTagName("username")
    if len(usrNodes) != 0:
        usr = usrNodes[0].firstChild.nodeValue
        self.parameters["usr"] = usr

    pwNodes = apnNode.getElementsByTagName("password")
    if len(pwNodes) != 0:
        pw = pwNodes[0].firstChild.nodeValue
        self.parameters["pw"] = pw

  def getProviderFromUser(self):
    self.countryCode = self.selectCountryCode()
    self.getProviders()
    self.chooseProvider()

if __name__ == "__main__":

  mkwvconf = Mkwvconf()

  mkwvconf.displayIntro()
  mkwvconf.getProviderFromUser()
  mkwvconf.makeConfig()
