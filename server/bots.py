# Part of UNMOVIE
# Copyright (C) 2002 Axel Heide

import time,traceback,random
from flash import *
from twisted.internet import threads,reactor,protocol,defer

import types
import operator
from cobe.brain import Brain


def deferLater(delay, callable, *args, **kw):

    d = defer.Deferred()
    d.addCallback(lambda ignored: callable(*args, **kw))
    delayedCall = reactor.callLater(delay, d.callback, None)
    return d

class KeywordBrain(Brain):
        
    def keywords(self, text):
        """Reply to a string of text. If the input is not already
        Unicode, it will be decoded as utf-8."""
        if type(text) != types.UnicodeType:
            # Assume that non-Unicode text is encoded as utf-8, which
            # should be somewhat safe in the modern world.
            text = text.decode("utf-8", "ignore")

        tokens = self.tokenizer.split(text)
        input_ids = map(self.graph.get_token_by_text, tokens)

        # filter out unknown words and non-words from the potential pivots
        pivot_set = self._filter_pivots(input_ids)
        keywords = self.get_word_tokens(pivot_set)
        logger_debug.writeLog("kewords: " + ":".join(keywords))
        return keywords
    
    def get_word_tokens(self, token_ids):
        q = "SELECT text FROM tokens WHERE id IN %s AND is_word = 1" % \
                self.graph.get_seq_expr(token_ids)

        rows = self.graph._conn.execute(q)
        if rows:
            return map(operator.itemgetter(0), rows)


class FlashBotChatter(FlashChatter):
    
    """
       Flash XML Bot Perspective
       
       this is the Perspective of the Flash Client
       The movement in space and the group functionality
    """
    """ some constants on bots behaviour """

    brain = None
    initialAvoidsLeft = random.randint(6,9)
    initialRepliesLeft = random.randint(3,6)
    #i'll count the down
    repliesLeft = initialRepliesLeft
    avoidsLeft = initialAvoidsLeft
    receiver = ""
    message = ""
    keywords = ""
    
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
        self.brain = KeywordBrain(self.name)
        self.loadBrain()
                
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
        #print self.name,args[1]

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
        #print self.participant.name
        pass
        
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
        #self.service.sendParticipants(self.name,"botkeys",{"text":keywords,"sender":self.name})
               
    def failure(self,fail=None):
        self.debug("something wrong %s" % fail.getErrorMessage())
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
        if self.brain:
            d1 = deferLater(0,self.brain.reply,self.message)
            d1.addCallbacks(self.sendAnswer,self.failure)
            d2 = deferLater(0,self.brain.keywords,self.message)
            d2.addCallbacks(self.sendKeywords,self.failure)
        #self.message = ""
        if self.repliesLeft: self.repliesLeft -= 1 


    def loadBrain(self):
        self.participant.setLocation((random.randint(0,768),random.randint(0,576)))
        self.changeLocation()
        self.service.addParticipant(self.participant)

