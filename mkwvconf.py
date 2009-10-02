#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import string
import os
from xml import xpath
from xml.dom.minidom import parse

#change these to the correct pats for your distribution
xmlPath = '/usr/share/mobile-broadband-provider-info/serviceproviders.xml'
configPath = '/etc/wvdial.conf'

def clrScr():
    os.system('clear')

def getCountryCode():
    """prints introduction, then displays a list of country codes contained in the provider database from which the user must choose one"""
    l = []
    nodes = getNodesFromXml("country/@code")
    for n in nodes:
        l.append(str(n.value))
    clrScr()

    displayIntroduction()

    print "\nAvailable country codes:\n"
    print l
    
    input = ""
    
    while not input in l:
        input = raw_input("\nGet providers for which country code? : ")
    return input
    
def getNodesFromXml(xquery):
    """returns results of xquery as a list"""
    doc = parse(xmlPath)
    return xpath.Evaluate(xquery, doc.documentElement)

def getProviders(countryCode):
    """returns a dictionary of providers for the specified country code"""
    nodes = getNodesFromXml('country[@code=\'' + countryCode +  '\']/provider/name')
    d = {}
    i = 0
    for n in nodes:
        d[i] = n.firstChild.nodeValue
        i+=1
    return d
    
def chooseProvider(providers):
    """returns provider chosen by user"""
    max =0
    clrScr()
    print "\nProviders for '" + countryCode + "':\n"
    for k, v in providers.items():
        print str(k) + ": " + v
        if k > max:
            max = k
            
    input = -1
        
    while input > max or input < 0:
        inputStr = getUserInput("Choose a provider [0-" + str(max) + "]:")
        try:
            input = string.atoi(inputStr)
            if input < 0 or input > max:
                print "Input needs to be between 0 and " + str(max)
        except:
            input = -1
            print "Input needs to be an integer."
        
    return  providers[int(input)]
    
def makeConfig(countryCode, chosenProvider):
    """assembles configuration section using information provided by user. the configuration is either written to wvdial.conf or printed for manual insertion"""
    nodes = getNodesFromXml("country[@code='" + countryCode +  "']/provider[name='" + chosenProvider + "']")
    parameters = parseProviderNode(nodes[0])
    
    parameters["modem"] =  getModemDevice()
    parameters["profileName"] = getUserInput("Enter name for configuration: ","DefaultProfile")

    editConf = raw_input("\nDo you want me to try to modify " + configPath + " (you will need superuser rights)? Y/n: ")
    clrScr()
    if editConf in ["", "Y",  "y"]:
        writeConfig(parameters)
    else:
        print "\n\nDone. Insert the following into " + configPath + " and run 'wvdial " + parameters["profileName"] + "' to start the connection.\n\n"
        print formatConfig(parameters)
    
def writeConfig(parameters):    
    """append or replace the configuration section to wvdial.conf"""
    if not os.path.exists(configPath):
        print "\nWarning: " + configPath + " doesn't exist, creating new file."        
        f = open(configPath, 'w')
        f.close()
    
    f = open(configPath, 'r')
    text = f.read()
    f.close()
    
    snippetStart = text.find("[Dialer %(profileName)s]" % parameters)
    if snippetStart != -1:
        snippetEnd = text.find("[Dialer ", snippetStart+1)
        print "\nThe following part of wvdial.conf will be replaced: \n\n" + text[snippetStart:snippetEnd]
        print "by: \n\n" + formatConfig(parameters)
        text = text.replace(text[snippetStart:snippetEnd], formatConfig(parameters))
    else:
        print "\nThe following will be appended to wvdial.conf: \n\n" + formatConfig(parameters)
        text += "\n" + formatConfig(parameters)
    
    editConf = raw_input("Write to file? Y/n: ")
    if editConf in ["", "Y",  "y"]:
        f = open(configPath, 'w')
        f.write(text)
        f.close()
        
        print "wvdial.conf edited successfully, run 'wvdial " + parameters["profileName"] + "' to start the connection.\n\n"
    
def formatConfig(parameters):
    """formats the information contained in parameters into a valid wvdial.conf format"""
    
    if not 'usr' in parameters:
        parameters['usr'] = ""
        
    if not 'pw' in parameters:
        parameters['pw'] = ""
    
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
""" % parameters
    
def getModemDevice():
    """return modem location provided by user"""
    defaultLocation = "/dev/ttyUSB0"
    input = "initialValue"
    
    while not input.startswith("/dev/") or len(input) == 0:
        input = getUserInput("Enter modem location (default is /dev/ttyUSB0): ",  defaultLocation)
    
    if len(input.strip()) == 0:
        input = defaultLocation
    
    return input
    
def getUserInput(prompt, default=""):
    """utility method for getting user input. displays prompt, optional default fallback"""
    accept = "n"
    inp = ""
    while accept == "n" or accept == "N":
        inp = raw_input("\n" + prompt)
        if len(inp.strip()) == 0:
            inp = default
        accept = raw_input("Your choice: '" + inp + "'. Is this correct? Y/n: ")
    return inp

def parseProviderNode(node):
    """fill parameter dictionary from provider xml node"""
    d = {}
    
    apnNode = node.getElementsByTagName("apn")[0]
    apn = apnNode.getAttribute("value")
    d["apn"] = apn
    
    usrNodes = apnNode.getElementsByTagName("username")
    if len(usrNodes) != 0:
        usr = usrNodes[0].firstChild.nodeValue
        d["usr"] = usr
    
    pwNodes = apnNode.getElementsByTagName("password")
    if len(pwNodes) != 0:
        pw = pwNodes[0].firstChild.nodeValue
        d["pw"] = pw
    
    return d

def displayIntroduction():
    print u"""
mkwvconf automatically generates a dialer section for use in wvdial.conf based on mobile-broadband-provider-info.

If a provider is missing from the list, add a bug at http://bugzilla.gnome.org/enter_bug.cgi?product=NetworkManager (include your provider name, your country, your plans marketing name if you know it, and of course the APN you're using for data). For more information about the mobile broadband provider database, see http://blogs.gnome.org/dcbw/2009/06/22/mobile-broadband-assistant-makes-it-easy/ .

The configuration generated by mkwvconf overwrites CID 1 with your provider info ('Init2=AT+CGDCONT=1,...') which is then called by dialing *99***1# (the digit before the trailing '#' specifies which CID to use).

Further reading on APNs can be found here: http://mail.gnome.org/archives/networkmanager-list/2008-August/msg00191.html. Thanks goes to Antti Kaijanmäki for explanations and links!
    """

if __name__ == "__main__":
    countryCode = getCountryCode()
    providers = getProviders(countryCode)
    chosenProvider = chooseProvider(providers)
    makeConfig(countryCode, chosenProvider)
