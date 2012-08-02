#!/usr/bin/python
# Part of UNMOVIE
# Copyright (C) 2002 Axel Heide

from twisted.internet import  tcp
from twisted.python import logfile,failure

from twisted.internet.protocol import Protocol, Factory
from twisted.words import service
from twisted.words.service import IWordsClient

from twisted.spread import pb
from twisted.web import server
import sys,string,random

from time import strftime,localtime,time
import xml.dom.minidom as xmldom
import string,traceback

import grid

def minidom_namednodemap_has_key(self, key):
  """a has_key method for minidom's namednodemap, because I like has_key"""  
  if type(key) is types.TupleType:
    return self._attrsNS.has_key(key)
  else:
    return self._attrs.has_key(key)

xmldom.AttributeList.has_key = minidom_namednodemap_has_key

NUL = chr(0)
CR = chr(015)
NL = chr(012)
LF = NL
SPC = chr(040)

### some shortcuts
MOVE_UP = (0,1)
MOVE_DOWN = (0,-1)
MOVE_LEFT = (-1,0)
MOVE_RIGHT = (1,0)
movements = {'up':MOVE_UP,'down':MOVE_DOWN,'left':MOVE_LEFT,'right':MOVE_RIGHT}
 
def randomDirection():
    return movements.values()[random.randint(0,3)]

OFFLINE = 0
ONLINE  = 1
AWAY = 2
AVOID = 3
SEARCH = 4
TALK = 5
LISTEN = 6
STREAM = 7

USERS_ALLOWED = 4

statuses = ["Offline","Online","Away","avoiding conversation","searching conversation","talking","listening","streaming"]


### some error_codes

ProtocolError = "ProtocolError"
InsufficientParams = "InsufficientParams"
CommandNotFound = "CommandNotFound"
UserNotFound = "UserNotFound"
alreadyConnected = "alreadyConnected"
UserNotAvailable = "UserNotAvailable"

def timestr():
  return strftime("%a, %d %b %Y %H:%M:%S", localtime())

class Logger:
    def __init__(self,name): 
        self.name = "%s.log" % name 
        self.dir = "logs"
        self.log = logfile.LogFile(self.name, self.dir, None)
    
    def writeLog(self,msg):
        self.log._openFile()
        self.log.write("%s - %s\n" % (timestr(),`msg`))
        self.log.close()
	
logger = Logger("access")
logger_err = Logger("error")
logger_debug = Logger("debug")



class FlashProtocol(Protocol):
    """
       Flash XML Messaging protocol.
       A (very) minimalistic interface for XML Socket connections used in Flash
       This is all about sending and receiving xml formatted messages the commands
       that these messages invoke are in a subclass
    """

    buffer = ""
    
    def sendLine(self, line):
        try:
            self.transport.write("%s%s" % (str(line), NUL))
        except:
            logger_err.writeLog(traceback.print_exc())
        #print line

    def sendMessage(self, command, parameter_list={}):
        """Send a line formatted as an Flash XML message.

        First argument is the command, all subsequent arguments
        are parameters to that command .
        
        i.e. <msg text="foo" user="bar" /> 
             command=msg parameter_list={"text":"foo","user":"bar"} 
        """
        if not command:
            raise ValueError, "sendMessage requires a command."

        if ' ' in command or command[0] == ':':
            raise ValueError, "Somebody screwed up, 'cuz this doesn't" \
                  " look like a command to me: %s" % command
        line = ""
        if type(parameter_list) == dict:
            for key,val in parameter_list.items():
                line += " %s='%s' " % (key,val)
        self.sendLine("<"+ command + line +" />")

    def dataReceived(self, data):
        """
        """
        self.buffer = self.buffer + data
        lines = string.split(self.buffer, NUL)
        command = None
        params = None

        try:
            for line in lines:
                if len(line) <= 2:
                # This is a blank line, at best.
                    continue
                if line[-2] == ( CR+LF or LF+CR ):
                    line = line[:-1]
                if line[-1] == ( CR or LF ):
                    line = line[:-1]
                try:
                    doc = xmldom.parseString(line)
                    for node in doc.childNodes:
                        params = dict()
                        command = node.nodeName
                        for item in node.attributes.items():
                            params[item[0]] = item[1]
                        break
                except:
                    logger_err.writeLog(traceback.print_exc())
                    raise ProtocolError

            method = getattr(self, "flash_%s" % command, None)
            if method is not None:
                method(params)
            elif command == "policy-file-request":
                logger_err.writeLog("got a flash security request")
                self.sendLine('''<?xml version="1.0"?><!DOCTYPE cross-domain-policy SYSTEM "http://www.adobe.com/xml/dtds/cross-domain-policy.dtd"><cross-domain-policy><allow-access-from domain="*" to-ports="*" /></cross-domain-policy>''')
            else:
                self.command_unknown(command, params)
                
        except NotImplementedError:
            text = "function flash_%s is not implemented" % command
            self.sendMessage("error",{"text":text})
        except ProtocolError:
            self.sendMessage("error",{"text":"xml is garbled"})
        except UserNotFound:
            self.sendMessage("error",{"text":"user was not found"})
        except UserNotAvailable:
            self.sendMessage("error",{"text":"user is not available"})
        except alreadyConnected:
            self.sendMessage("error",{"text":"user is already connected"})
        except InsufficientParams:
            self.sendMessage("error",{"text":"insufficient parameters"})
        except pb.Error:
            pass
        except:
            self.buffer = ""
            print "cant process command %s" % traceback.print_exc()
        self.buffer = ""
                 
    def command_unknown(self,command, params):
        """Implement me!"""
        raise NotImplementedError
     
        
class FlashChatter(FlashProtocol,service.WordsClient):

    __implements__ = IWordsClient
    """
       Flash XML Client implementation.
       
       
       every command beginning with flash_ can be invoked with a 
       xml - message sent by the flash client 
       
       It's an interface to allow the message handling to and from the client
    
    """

    name = '*'
    passwd = None
    participant = None
    pendingLogin = None
    pendingLocation = None
    group = []

    def callRemote(self, key, *args, **kw):
        apply(getattr(self, key), args,kw)

    def connectionMade(self):
        self.factory.numProtocols = self.factory.numProtocols+1

    def connectionLost(self,why=None):
        self.factory.numProtocols = self.factory.numProtocols-1
        if self.participant:
            self.service.removeParticipant(self.participant)
            self.participant.detached(self, self.identity)

    def receiveContactList(self, contactList):
        """ do i need this ?"""

    def notifyStatusChanged(self, name, status):
        logger_debug.writeLog("notifyStatusChanged %s %s" % (status,name))
        self.receiveDirectCommand("status",{"mode":status,"sender":name})

    def enterDiscussion(self,discussion):
        """ ad same actions when i enter a discussion """
        self.participant.changeStatus(LISTEN)

    def flash_connect(self, params):
        """
        so far i need a username and a location in screencoordinates
        """
        try: 
            name = params['user']
            self.pendingLocation = params['location']
        except: raise ProtocolError 
        
        participant=None
        
        if not self.participant:
            if name == "gast":
                for x in range(USERS_ALLOWED):
                    if self.service.getPerspectiveNamed("you_%d" % x).status == OFFLINE:
                        participant = self.service.getPerspectiveNamed("you_%d" % x)
                        break
            elif name == "zkm":
                for x in range(0,2):
                    if self.service.getPerspectiveNamed("me_%d" % x).status == OFFLINE:
                        participant = self.service.getPerspectiveNamed("me_%d" % x)
                        break
            else:
                try:
                    participant = self.service.getPerspectiveNamed(name)
                    if participant.status != OFFLINE: participant = None
                except:
                    participant = None 
            if not participant:
                raise UserNotAvailable
            self.logInAs(participant)
        else:
            raise alreadyConnected

    def flash_msg(self, params):
        """Send a (private) message.
        Parameters: <receiver> <text to be sent>
        [REQUIRED]
        """
        if params.has_key('receiver'): name = params['receiver']
        else: 
            if self.participant: 
                group = self.service.groupOfParticipant(self.participant)
                if group: 
                    member_avail = filter(lambda x:x.status == LISTEN and x.name != self.name,group.members)
                    if member_avail:
                        member = member_avail.pop()
                        name = member.name
            else:
                self.notLoggedIn()
                return
        if params.has_key('text'): text = params['text']
        else: return

        logger.writeLog("%s@%s said:'%s'" % (self.name,self.transport.hostname,text))
         
        if self.participant:
            msgMethod = self.participant.directMessage
            try:
                self.service.sendParticipants(self.name,"botmsg",{"text":text,"sender":self.name})
                msgMethod(name,text)
            except:
                self.receiveDirectCommand("msg",{"sender":"MsgServ","text":"cant send text, probably there is no user to listen"})
        else:
            self.notLoggedIn()            

    def flash_broadcast(self,params):
        """Send a  message to everyoune in the room.
        Parameters: <text to be sent>
        [REQUIRED]
        """
        text = params['text']
        if self.participant:
            self.service.sendParticipants(self.name,'msg',{"text":text,"sender":self.name})
        else:
            self.notLoggedIn()            

    def flash_move(self,params):
        """ Tries to move the location of the user
        Parameters: <direction>
        [REQUIRED]
        """
        direction = params['direction']
        avoid = 0
        if params.has_key('avoid'): avoid = 1
        (x,y) = self.service.grid.requestLocation(self.participant,direction,1,avoid)

        group = self.service.groupOfParticipant(self.participant)

        if group:
            if len(group.members) == 1:
                self.service.removeParticipantFromDisussion(self.name)
            else:
                if self.participant.status == AVOID:
                    self.service.removeParticipantFromDisussion(self.name)
                else:
                    self.receiveDirectCommand("group",{"members":string.join(map(lambda x:x.name,group.members),";")})
                    return 0

        self.participant.setLocation((x,y)) 
        self.receiveDirectCommand("location",{"x":x,"y":y,"sender":self.name})
        self.service.sendParticipants(self.name,"location",{"x":x,"y":y,"sender":self.name})

        
    def flash_status(self,params):
        mode = int(params['mode'])
        logger_debug.writeLog("> %s %s" % (mode,statuses))
        if mode < len(statuses):
           try:
               self.participant.changeStatus(mode)
           except:
               logger_err.writeLog(">%s" % traceback.print_exc())
        
    def flash_getMovies(self,params):
        list = self.service.retrieveWords()
        try:
            logger_debug.writeLog(`list`)
        except:
            pass
        self.receiveDirectCommand("videos",{"sender":"VideoServ","text":`list`})
    
    def flash_getMovie(self,params):    
        list = self.service.retrieveWords()
        try:
            logger_debug.writeLog(`list`)
        except:
            pass
    
    def flash_location(self,params):
        """ updates the location to snap to the grid (do we really need this?
        Parameters: <location>
        [REQUIRED]
        """
        loc = params['location']
        if self.participant:
            if self.service.groupOfParticipant(self) and self.participant.status != AVOID:
                self.participant.changeStatus(LISTEN)
            #print loc
            (x,y) = self.service.grid.conformToGrid(loc)
            self.participant.setLocation((x,y))
            self.receiveDirectCommand("location",{"x":x,"y":y})
            
        else:
            self.notLoggedIn()          

    def flash_dump(self,params):
        self.sendMessage("dump",{"text":self.service.showParticipant()})
        
    def receiveDirectMessage(self, sender, message, metadata = None):
        """ to stay consistent with the words service """
        try:
            self.receiveDirectCommand("msg",{"sender":sender,"text":message})
        except:
            raise CommandNotFound

    def receiveDirectCommand(self, *args, **kw):
        if not args: return
        try:
            apply(self.sendMessage,args,kw)
        except:
            raise CommandNotFound,args

    def memberLeave(self): 
        try:
            #self.participant.changeStatus(AVOID)
            self.flash_move({"direction":randomDirection(),'avoid':1})
            #logger_debug.writeLog("%s has left group %s" % (self.name,group))
        except:
            print traceback.print_exc()    
        
    def successfulLogin(self,ident):
        self.identity = ident
        self.pendingLogin.attached(self, self.identity)
        self.participant = self.pendingLogin
        #self.participant.changeStatus(service.ONLINE)
        logger_debug.writeLog("pending" + self.pendingLocation)
        (x,y) = self.participant.setLocation(self.service.grid.conformToGrid(self.pendingLocation))
        self.service.addParticipant(self.participant)
        self.name = self.participant.name
        # confirm myself that i have sucsessfully logged in
        self.sendMessage("login",{"user":self.name,"x":x,"y":y})
        allusers = string.join(self.service.getParticipantList(),":")
        alllocs = string.join(map(lambda x:str(x)[1:-1],self.service.getParticipantLocations()),":")
        allstati = string.join(map(lambda x:str(x.status),self.service._participantsPerspectives()),":")
        msg = {"users":allusers,"statuses":str(allstati),"locations":str(alllocs)}
        self.sendMessage("users",msg)
        self.service.sendParticipants(self.name,"users",msg)
        logger.writeLog("%s@%s joined" % (self.name,self.transport.hostname))
        del self.pendingLogin
        del self.pendingLocation
              

    def logInAs(self, participant):
        self.pendingLogin = participant
        req = self.service.authorizer.getIdentityRequest(participant.name)
        req.addCallbacks(self.successfulLogin, self.notLoggedIn)

    def notLoggedIn(self, message=""):
        """Login failed.
        """
        self.receiveDirectCommand("msg",{"sender":"NickServ", "text": "You haven't logged in yet."})
        raise UserNotFound
        
    def debug(self,message="",*args ):
        try:
            logger_debug.writeLog("%s|%s -- %s" % (self.name,statuses[self.participant.status],message))
        except:
            logger_err.writeLog(traceback.print_exc())
            
            
class FlashMember(service.Participant):
    
    """
       Flash XML Client Perspective
       
       this is the Perspective of the Flash Client
       The movement in space and the group functionality
    """
    location = ()
    
    def getLocation(self):
        return self.location
    
    def setLocation(self,point):
        self.location = point
        return self.location

    def changeStatus(self, newStatus):
        self.status = newStatus
        self.service.sendParticipants(self.name,'status',{"mode":self.status,"sender":self.name})

    def detached(self, client, identity):
        self.client = None
        self.changeStatus(OFFLINE)


        
class FlashDiscussion(service.Group):

    """
       Flash XML Discussion
       this is only pseudocode so far
       the members join groups according to their movements
       i sublass service.Group to get in  space 
    """

    def __init__(self, name=0):
        self.name = name
        self.members = []

    def addMember(self, participant):
        if participant not in self.members:
            self.members.append(participant)
        participant.client.enterDiscussion(self)
        participant.client.group = self.listMembers
        logger_debug.writeLog(self.listMembers())

                                   
    def removeMember(self, participant):
        try:
            self.members.remove(participant)
            participant.client.memberLeave()
            #for member in self.members:
            #    member.memberLeft(participant, self)    
            if not self.listMembers() < 2:
                return self
            else:
                return 0
     
        except ValueError:
            logger_err.writeLog("%s %s" & (self.name, participant.name))

    def listMembers(self):
        return self.members
     
class FlashService(service.Service):

    """
       Flash XML Discussion
       This keeps track of all Users in the room as well as the Discussions and the Grid
    """
    
    def __init__(self, serviceName, serviceParent=None, authorizer=None, application=None):
        self.groups = []
        """ participants {name:FlashPerspective.getLoc,} """
        self.participants = {}
        self.grid = grid.Grid()
        self.grid.participants = self.participants
        self.grid.service = self
        self.videoserver = None
        self.group_count = 0
        self.connectVideoServer()
        pb.Service.__init__(self, serviceName, serviceParent, authorizer)
    
    def connectVideoServer(self): 
        pb.connect("localhost",8788,
            "video", "****",
            "video_server",'video', 2).addCallbacks(self.registerVideoServer)
    
    def registerVideoServer(self,persp):
        self.videoserver = persp
        # test connection
        self.addWords(['hallo','gomorra'],'tester','test')    

    def video_connerror(self,which):
        print "failure: %s" %  which
        
    def addWords(self,words,participant,group):
        if words:
            try:
                callB = self.videoserver.callRemote('addWord',words,participant,group)
                callB.addCallback(self.addWordsSucess)
                callB.addErrback(self.video_connerror)
            except: 
                logger_debug.writeLog("videoserver trying to send")
                self.connectVideoServer()
 
    def addWordsSucess(self,whichWords):
        print "success: %s" % whichWords

    def removeParticipant(self,participant):
        try:
            self.removeParticipantFromDisussion(participant.name)
            del self.participants[participant.name]        
            for contact in self._participantsPerspectives():
                contact.client.notifyStatusChanged(participant.name,0)
        except KeyError:
            raise ProtocolError
        logger.writeLog("%s@%s left" % (participant.name,participant.client.transport.hostname))
            
    def getParticipantList(self):            
        return self.participants.keys()

    def getParticipantLocations(self):            
        return map(lambda x:x(),self.participants.values())
    
    def sendVideo(self,video):
        try:
            logger_debug.writeLog("videoserver trying to send")
        except:
            pass
        for contact in self._participantsPerspectives():
            #if (contact.status == STREAM) and video: 
            if video: 
                contact.client.receiveDirectCommand("video",{"id":`video`})
       
    def getParticipantByStatus(self,status,participant=None): 
        persp = self._participantsPerspectives()
        if type(status) == list:
            persp_return = filter(lambda x:x.status in status and x != participant,persp)     
        else:
            persp_return = filter(lambda x:x.status == status and x != participant,persp)     
        return persp_return

    def showParticipant(self):
        return `self.participants`
    
    def cleanupDiscussions(self):
        for group in self.groups:
            for toRemove in filter(lambda x:x.status not in [LISTEN,TALK],group.members):
                self.removeParticipantFromDisussion(toRemove.name)
    
    def storeWords(self,participant,words):
        part = self.getPerspectiveNamed(participant)
        group = self.groupOfParticipant(part)
        if group:
            try:
                self.addWords(words,participant,group.name)
            except:
                traceback.print_exc()
                
    def removeParticipantFromDisussion(self,participant):
        part = self.getPerspectiveNamed(participant)
        #part.changeStatus(AVOID)
        group = self.groupOfParticipant(part)
        if group: 
            logger_debug.writeLog("leaves discussion with %s" % (map(lambda x:x.name,group.members)))
            if group.removeMember(part):
                for member in group.members:
                    group.removeMember(member)
                del group
            return 1
        else: return 0

    def addParticipant(self,participant):
        """ 
        """
        for contact in self._participantsPerspectives():
            contact.client.notifyStatusChanged(participant.name,participant.status)
        try:self.participants[participant.name] = participant.getLocation
        except: logger_err.writeLog(traceback.print_exc())    

    def sendParticipants(self,name,*args,**kw):
        self.cleanupDiscussions()
        for contact in self._participantsPerspectives():
            if (contact.name != name) and args: 
                apply(contact.client.receiveDirectCommand,args,kw)

    def makeConversation(self,participant,other_participants):
        if not other_participants or not participant: return
        try:
            for group in self.groups:
                if filter(lambda member:member.name in other_participants,group.members):
                    #if participant in map(lambda part:part.name,group.members): return
                    group.addMember(self.getPerspectiveNamed(participant))
                    for other in other_participants:
                        group.addMember(self.getPerspectiveNamed(other))
                    return
            logger_debug.writeLog("making new group %s with %s" % (participant,other_participants) ) 
            self.group_count+=1
            newGroup = FlashDiscussion(self.group_count)
            newGroup.addMember(self.getPerspectiveNamed(participant))
            for other in other_participants:
                newGroup.addMember(self.getPerspectiveNamed(other))
            self.groups.append(newGroup)
            return

        except:
            logger_debug.writeLog("part: %s oters:%s" % (participant,other_participants))
            logger_err.writeLog(traceback.print_exc())          
                
    def _participantsPerspectives(self):
        return map(lambda contact:self.getPerspectiveNamed(contact),self.participants.keys())
    
    def groupOfParticipant(self,participant):
        for group in self.groups:
            if participant in group.members: 
                #if len(group.members) == 1:
                    #return None
                return group
        return None

class FlashFactory(Factory):
        
    def __init__(self, service,host,port):
        self.numProtocols  = 0
        self.service = service
        self.host, self.port = host, port
        
    def buildProtocol(self, connection,bot=0):
        import flash
        i = flash.FlashChatter()
        i.service = self.service
        i.factory = self
        return i

    
def main():
    from twisted.internet.app import Application
    from twisted.cred.identity import Identity

    from twisted.cred.authorizer import DefaultAuthorizer
    from twisted.manhole.telnet import ShellFactory

    import flashweb
    import flash
    import bots  
    
    def add_user(ident_name,password="",serv_name=""):
        persp_name = ident_name
        persp = svc.createPerspective(persp_name)
        ident = auth.createIdentity(ident_name)
        #ident.setPassword(password)
        
        ident.addKeyByString("unmovie_service", persp_name)
        auth.addIdentity(ident)
        return persp,ident

    def add_bot(ident_name,password="",params=[]):
        persp_name = ident_name + "_perspective"
        part,ident = add_user(ident_name,password)
        bot = bots.FlashBotChatter()
        bot.participant = part.attached(bot,ident_name)
        bot.service = svc
        bot.name = ident_name
        bot.setInitialValues(params)
        return bot
 
    
    appl = Application("unmovie")
    auth = DefaultAuthorizer(appl)

    svc = flash.FlashService("unmovie_service",appl,auth)
    svc.perspectiveClass = flash.FlashMember    
    
    add_user("axel")
    add_user('philip')
    
    for x in range(0,2):
        add_user("me_%d" % x)
    for x in range(USERS_ALLOWED):
        add_user("you_%d" % x)
    
    # nietzsche = add_bot("nietzsche",params=[20,10,20,5,6,30])
    # dylan = add_bot("dylan",params=[8,12,40,7,3,20])
    # tark = add_bot("tark",params=[12,7,17,6,2,14])
    # geisha = add_bot("geisha",params=[7,16,70,6,2,20])
    # dogen = add_bot("dogen",params=[7,7,40,6,4,40])

    nietzsche = add_bot("nietzsche",params=[20,10,20,5,6,10])
    dylan = add_bot("dylan",params=[8,12,40,7,3,8])
    tark = add_bot("tark",params=[12,7,17,6,2,6])
    geisha = add_bot("geisha",params=[7,16,70,6,2,8])
    dogen = add_bot("dogen",params=[7,7,40,6,4,7])
    
    fls = FlashFactory(svc,"******","9998")
   
    # sf = ShellFactory()
    # sf.username = 'axel'
    # sf.password = '****'
    # sf.namespace['server'] = svc
    # sf.namespace['factory'] = fls
    #  
    # appl.listenTCP(8780, sf)
    # adm = server.Site(flashweb.WordsGadget(svc))
    appl.listenTCP(9998,fls)
    # appl.listenTCP(9996,pb.BrokerFactory(pb.AuthRoot(auth)))
    # appl.listenTCP(9997,adm)

    
    appl.run()

if __name__ == '__main__':
    main()
