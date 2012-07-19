# Part of UNMOVIE
# Copyright (C) 2002 Axel Heide

import time,traceback,random
from flash import *
from twisted.internet import threads,reactor,protocol
from twisted.spread import pb


class FlashBotChatter(FlashChatter):
    
    """
       Flash XML Bot Perspective
       
       this is the Perspective of the Flash Client
       The movement in space and the group functionality
    """
    """ some constants on bots behaviour """

    perspective = None
    initialAvoidsLeft = random.randint(6,9)
    initialRepliesLeft = random.randint(3,6)
    #i'll count the down
    repliesLeft = initialRepliesLeft
    avoidsLeft = initialAvoidsLeft
    receiver = ""
    message = ""
    keywords = ""
    connection = None
    
    """ some timeouts for bot actions """
    # if a bot is in a discussion and noone talks it will start after timeout secs
    timeoutBeforeTalkingWhenIdle = random.randint(20,60)
    # if a bot wants to leave a discussion it waits
    timeoutBeforeLeavingDiscussion = random.randint(2,5)
    # if a bot needs someone to talk to it searches in a loop this value is the timeout between attempts
    timeoutBeforeSearchingReceiver = random.randint(2,5)
    
    movementSpeed = 10
    
    """ ids of calllater requests """
    callLaterReq = None
    callLaterMov = None
    callLaterSpeakTimeout = None
    
    def setInitialValues(self,params):
        """ some timeouts for bot actions """
        self.initialAvoidsLeft = params[0]
        self.initialRepliesLeft = params[1]
        # if a bot is in a discussion and noone talks it will start after timeout secs
        self.timeoutBeforeTalkingWhenIdle = params[2]
        # if a bot wants to leave a discussion it waits
        self.timeoutBeforeLeavingDiscussion = params[3]
        # if a bot needs someone to talk to it searches in a loop this value is the timeout between attempts
        self.timeoutBeforeSearchingReceiver = params[4]
        self.movementSpeed = params[5]
        

    def connect_megahal(self):
        self.connection = pb.connect("localhost",8787,self.name, "****","megahalservice", None, 2)
        self.connection.addCallback(self.loadBrain)
        self.connection.addErrback(self.failure)
        
    def receiveDirectMessage(self, sender, message, metadata = None):
        self.debug("message received! from: %s" % (sender))
        self.receiver = sender
        self.message = message
        try:
            if sender != self.name and self.participant.status in [LISTEN,TALK]: 
                self.callLaterSpeakTimeout = reactor.callLater(len(message)/8,self.reply)
        except:
            raise CommandNotFound

    def receiveDirectCommand(self, *args, **kw):
        if not args: return
        if args[0] == "msg":
            try:
                apply(self.receiveDirectMessage,(args[1]['sender'],args[1]['text']))
            except:
                self.debug(traceback.print_exc())

    def sendUser(self,msg):
        try:
            participant = self.service.getPerspectiveNamed(self.receiver)    
            self.debug("message sent! to: %s :: %s" % (self.receiver,msg))
            if participant: 
                participant.client.receiveDirectCommand("msg",{"sender":self.name, "text":msg})
            self.service.sendParticipants(self.name,"botmsg",{"text":msg,"sender":self.name})
            #self.service.generateVideo(msg)
        except:
            self.debug(traceback.print_exc())
            
    def flash_msg(self, params):
        return 0
        
    def flash_status(self,params):
        return 0
        
    def flash_move(self,params):
        """ Tries to move the location of the user
        Parameters: <direction>
        [REQUIRED]
        """
        direction = params['direction']
            
        (x,y) = self.service.grid.requestLocation(self.participant,direction)
        if self.participant.status in [LISTEN,TALK]: 
            logger_debug.writeLog("halt this event!")
            return
 
        self.participant.setLocation((x,y)) 
        self.receiveDirectCommand("location",{"x":x,"y":y,"sender":self.name})
        self.service.sendParticipants(self.name,"location",{"x":x,"y":y,"sender":self.name})

        group = self.service.groupOfParticipant(self.participant)

        if group:
            logger_debug.writeLog("%s flash_move status %d" % (self.name,self.participant.status))
            logger_debug.writeLog("%s flash_move from discussion" % self.name)
            self.participant.status = flash.AVOID
            self.avoidsLeft = self.initialAvoidsLeft
            self.service.removeParticipantFromDisussion(self.participant.name)


    def login(self,factory = None):
        """ i need a func to programatically login the bot. it's a bot, mind you """
        self.participant.changeStatus(ONLINE)

    def logout(self,persp):
        """ logout the bot """
        self.participant.changeStatus(OFFLINE)

    def changeLocation(self):
        """ i want to move  """
        logger_debug.writeLog("%s change location" % self.participant.name)
        # dont move when you are listening or talking
        #print self.name + " " +statuses[self.participant.status] 
        if self.participant.status in [AVOID,ONLINE]: self.avoidsLeft -= 1
        if not self.avoidsLeft:
            self.participant.changeStatus(SEARCH)
            self.avoidsLeft = self.initialAvoidsLeft
 
        try: 
            if self.callLaterMov: self.callLaterMov.cancel()
        except: pass
        
        if self.participant.status in [SEARCH,AVOID,ONLINE]:
            self.debug("get a new loc")
            self.callLaterMov = reactor.callLater(self.movementSpeed,self.changeLocation)
            newDirection = self.service.grid.requestDirection(self.participant)
            self.flash_move({"direction":newDirection})
           
    def enterDiscussion(self,discussion):
        """ ad same actions when i enter a discussion """
        self.participant.changeStatus(LISTEN)
        try: self.callLaterMov.cancel()
        except: pass
 
        logger_debug.writeLog("%s enterDiscussion" % self.participant.name)
        self.callLaterSpeakTimeout = reactor.callLater(self.timeoutBeforeTalkingWhenIdle,self.reply)
        
    def leaveDiscussion(self):
        self.service.removeParticipantFromDisussion(self.participant.name)
        try: 
            self.timeoutBeforeSearchingReceiver.cancel()
        except:
            pass
        
    def memberLeave(self):
        #self.participant.changeStatus(AVOID)
        print self.participant.name
        
    def finishTalking(self):
        if self.repliesLeft: 
            """ if i am allowed to talk i will talk"""
            self.participant.changeStatus(LISTEN)
            self.callLaterSpeakTimeout = reactor.callLater(self.timeoutBeforeTalkingWhenIdle,self.reply)
        else: 
            logger_debug.writeLog("%s finishTalking" % self.participant.name)
            self.repliesLeft = self.initialRepliesLeft
            self.participant.changeStatus(AVOID)
            self.avoidsLeft = self.initialAvoidsLeft
            self.callLaterMov = reactor.callLater(self.timeoutBeforeLeavingDiscussion,self.changeLocation)
            self.leaveDiscussion()
            self.debug("try to leave discussion")

    def getSomeReceiver(self):
        try: 
            if self.participant.status == AVOID:
                self.service.removeParticipantFromDisussion(self.participant.name)
                for group in self.service.groups:
                    if group.members:
                    	logger_debug.writeLog("%s %s" % (len(group.members),map(lambda x:x.name,group.members)))
                    else:
                        logger_debug.writeLog("gruppe leer")
                self.debug("force remove from group")
                group = None
               
            
            group = self.service.groupOfParticipant(self.participant)
            if not group or len(group.members) == 1: 
                self.repliesLeft = 0
                self.finishTalking()
                return None
            self.debug("none to talk to %s" % map(lambda x:(statuses[x.status],x.name),group.members))
            member_avail = filter(lambda x:x.status == LISTEN and x.name != self.name,group.members)
            if member_avail: return member_avail.pop()
            else: return 0
        except:
            self.debug(traceback.print_exc())

    def sendAnswer(self,answer):
        """ i send the answer, the bot is available to talk in some secs 
        i should be in status SPEAK here
        """
        timeout = len(answer)/3
        self.sendUser(answer)      
        self.callLaterReq = reactor.callLater(timeout,self.finishTalking)
       
    def sendKeywords(self,keywords):
        self.keywords = keywords
        self.service.storeWords(self.participant.name,keywords)
        self.service.sendParticipants(self.name,"botkeys",{"text":keywords,"sender":self.name})
               
    def failure(self,why=None):
        self.debug("something wrong %s" % `why`)
        self.connection = None
        #print "couldn't connect to botserver"

    def reply(self,receiver="",message=""):
        """ ask megahal in a thread for an answer and add a callback to send out this answer  """
        self.debug("reply" + receiver + message)
        if self.participant.status == AVOID: 
            self.callLaterMov = reactor.callLater(self.timeoutBeforeLeavingDiscussion,self.changeLocation)
            return
        if not receiver:
            new_receiver = self.getSomeReceiver()
            if not new_receiver: 
                reactor.callLater(self.timeoutBeforeSearchingReceiver,self.reply)
                return
            receiver = new_receiver.name
        if not message: 
            message = self.message or self.name
        if self.participant.status != LISTEN: return
        self.receiver = receiver
        self.message = message
        self.participant.changeStatus(TALK)
        if self.perspective:
            self.perspective.callRemote('answer', self.message).addCallbacks(self.sendAnswer,self.failure)
            self.perspective.callRemote('keywords', self.message).addCallbacks(self.sendKeywords,self.failure)
        #self.message = ""
        if self.repliesLeft: self.repliesLeft -= 1 


    def loadBrain(self,megahal_perspective):
        self.participant.setLocation((random.randint(0,768),random.randint(0,576)))
        self.changeLocation()
        self.service.addParticipant(self.participant)

        self.perspective = megahal_perspective
        self.perspective.callRemote('load', self.name).addErrback(self.logout)

