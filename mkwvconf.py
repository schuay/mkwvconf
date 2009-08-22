#!/usr/bin/python
#depends: mobile....., python, pyxml

import sys
from xml import xpath
from xml.dom.minidom import parse

xmlPath = '/usr/share/mobile-broadband-provider-info/serviceproviders.xml'

def getCountryCode():
    input = raw_input("\nGet providers for which country code? (us, at, de, ...): ")
    return input
    
def getNodesFromXml(xquery):
    doc = parse(xmlPath)
    return xpath.Evaluate(xquery, doc.documentElement)

def getProviders(countryCode):
    nodes = getNodesFromXml('country[@code=\'' + countryCode +  '\']/provider/name')
    d = {}
    i = 0
    for n in nodes:
        d[i] = n.firstChild.nodeValue
        i+=1
    return d
    
def chooseProvider(providers):
    max =0
    print "\nProviders for '" + countryCode + "':"
    for k, v in providers.items():
        print str(k) + ": " + v
        if k > max:
            max = k
        
    input = getUserInput("Choose a provider [0-" + str(max) + "]:")
        
    return  providers[int(input)]
    
def makeConfig(countryCode, chosenProvider):
    nodes = getNodesFromXml("country[@code='" + countryCode +  "']/provider[name='" + chosenProvider + "']")
    parameters = parseProviderNode(nodes[0])
    
    parameters["modem"] =  getModemDevice()
    parameters["profileName"] = "DefaultProfile"

    print "\n\nDone. Paste the following into /etc/wvdial.conf and run 'wvdial " + parameters["profileName"] + "' to start the connection.\n\n"
    print formatConfig(parameters)
    
def formatConfig(parameters):
    return \
"""[%(profileName)s]
Modem Type = Analog Modem
Phone = *99#
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
    defaultLocation = "/dev/ttyUSB0"
    input = getUserInput("Enter modem location (default is /dev/ttyUSB0): ",  defaultLocation)
    
    if len(input.strip()) == 0:
        input = defaultLocation
    
    return input
    
def getUserInput(prompt, default=""):
    accept = "n"
    inp = ""
    while accept == "n" or accept == "N":
        inp = raw_input("\n" + prompt)
        if len(inp.strip()) == 0:
            inp = default
        accept = raw_input("Your choice: '" + inp + "'. Is this correct? Y/n: ")
    return inp

def parseProviderNode(node):
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

if __name__ == "__main__":
    countryCode = getCountryCode()
    providers = getProviders(countryCode)
    chosenProvider = chooseProvider(providers)
    makeConfig(countryCode, chosenProvider)
