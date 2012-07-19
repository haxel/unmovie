# Part of UNMOVIE
# Copyright (C) 2002 Axel Heide

from twisted.enterprise import adbapi 
from twisted.spread import pb
from twisted.python import logfile
from twisted.internet import  defer
from twisted.internet.protocol import Factory

from flash import logger_debug
from flash import logger_err
from flash import logger
from flash import FlashProtocol

from time import strftime,localtime,time
import traceback
import string


class myConnectionPool(adbapi.ConnectionPool):
    # i know this is ugly, but hey, it works
    def _runQuery(self, args, kw):
        conn = self.connect()
        curs = conn.cursor()
        result = []
        for arg in args[0]:
            apply(curs.execute, (arg,), kw)
            result.append(curs.fetchall())
        curs.close()
        return result


class VideoServerError(pb.Error):
    def __init__(self, pName):
        self.pName = pName

    def __str__(self):
        return "[vidserv] '%s'" % (self.pName,)


class VideoDatabase(adbapi.Augmentation): 

    def getVideo(self,keylist): 
        import string
        # Define the query 
        sql = []
        if type(keylist) == list:
            #args = string.join(map(lambda x:" "+x,keylist)," ")
            for key in keylist:
               sql.append("SELECT @x:='%s' as word,id,(MATCH (descriptor) AGAINST ('%s') + MATCH (desc_user) AGAINST ('%s')) AS score FROM video WHERE (MATCH (descriptor) AGAINST ('%s') or  MATCH (desc_user) AGAINST ('%s')) AND type = 'bband' AND published='true'  LIMIT 25 ;\n" % (key,key,key,key,key))
	       
               sql.append("SELECT @x:='%s' as word,id,(MATCH (descriptor) AGAINST ('%s') + MATCH (desc_user) AGAINST ('%s')) AS score FROM video WHERE (MATCH (descriptor) AGAINST ('%s') or  MATCH (desc_user) AGAINST ('%s')) AND type = 'modem' AND published='true'  LIMIT 25 ;\n" % (key,key,key,key,key))

        else:
            raise VideoServerError("wrong query")
            ##args= keylist[3:-2]
            ##sql = "SELECT id FROM video WHERE  MATCH (descriptor) AGAINST ('%s') AS score  LIMIT 5 ORDER BY score" % str(args)
        
        # Run the query, and return a Deferred to the caller to add 
        # callbacks to.
        return self.runQuery(sql)


class Word:
    def __init__(self,word,participant,group):
        self.word = word
        self.score = 0
        self.videos = []
        self.participant = participant
        self.group = group
        self.timestamp = time()  
    
    def updateTime(self):
        self.timestamp = time()  
             
    def __compare (self, x, y):
        return cmp(x[self.score], y[self.score])
        
    #def __repr__(self):
        #return [self.timestamp,self.word,self.participant,self.videos]
        # return "%s - %s %s %s" % (self.timestamp,self.word,self.participant,`self.videos`)


class Videolist(logfile.LogFile):

    def __init__(self):
        self.words = []
        self.multiples = []
        self.directory = "logs"
        self.name = "videos.log"
        self.path = self.directory + "/" + self.name
        self.rotateLength = 10000
        self.service = None
        self._openFile()
    
    def toplist(self):
        top = self.words.sort()
        if len(top) > 10:
            return top[:10]
        else:
            return top
            
    def add(self,words,participant,group):
        if(len(self.words) > 1000): self.words = self.words[10:]
        words_new = []
        words_old = []
        try:
            words_new,words_old = self.filterWords(words)
        except:
            print traceback.print_exc()
        
        print "%s ###### %s" % (`words_new`,`words_old`)
        if words_new:
            for word in words_new:
                self.words.append(Word(word,participant,group))
            timestamp = time()
            defferedObj = self.generateVideo(words_new,words_old,participant,group,timestamp)
            return defferedObj
        else:
            raise VideoServerError("no words added")
    
    def getVideo(self,client = None,timestamp = None):
        """ return some new videos to the client """
        newest = self.getNewest(timestamp)
        if not newest: return 0;
        word = self.getNewest(timestamp).pop()
        
        videolist = {word.word:word.videos}
        if not client:
            self.service.sendClients(videolist,word.participant,word.group,word.timestamp)
        else:
            client.sendMovie(videolist,word.participant,word.group,word.timestamp)
          
    def updateWord(self,props):
        (word,video,score) = props
        for idx in self.words:
            if idx.word == word:
                idx.score = score
                if video not in idx.videos: idx.videos.append(video)
                print "update:" + word + " / "+ video 
        
    def weighWords(self,words):
        return
        
    def filterWords(self,words):
        # only take words longer than 3 chars
        words = filter(lambda x:len(x)>2,words)
        # only take words not in wordlist yet
        for word in self.words:
             if word.word in words:
                 word.updateTime()
        
        words_new = filter(lambda y:y not in map(lambda x:x.word,self.words),words)
        words_old = filter(lambda y:y not in map(lambda x:x.word,self.words),words)
        return words_new,words_old
            
    def generateVideo(self,words_new,words_old,participant,group,timestamp):
        def combineVidsData(videolist):
            #print videolist
            #print "%s - %s - %s - %s - %s" % (`videolist`,`words_new`,participant,group,timestamp)
            tmp = {}
            for videos in videolist:
                if videos:
                    for video in videos:
                        self.updateWord(video)
                        if tmp.has_key(video[0]): tmp[video[0]].append(video[1])
                        else: tmp[video[0]] = [video[1],]
                else:
                    continue
            #print tmp.keys()
            return tmp,participant,group,timestamp
        
        try:
            logger_debug.writeLog("videoserver sent: %s" % `words_new`)    
        except:
            print traceback.print_exc()
        
        if self.service:
            deferredObj = self.service.db.getVideo(words_new)
            deferredObj.addCallback(combineVidsData)
            deferredObj.addCallback(self.storeVideos)
            return deferredObj
        else:
            raise VideoServerError("no service?")
    
    def storeVideos(self,*args):
        try:
            (videolist,participant,group,timestamp) = args[0]
            self.service.sendClients(videolist,participant,group,timestamp)
            print videolist
            if videolist:
                words = []
                for word,videos in videolist.items():
                    #self.write("<video word='%s' part='%s' group='%s' timestamp='%s'>\n" % (word,participant,group,timestamp))
                    #for video in videos:
                    #   self.write("\t<file id='%s'>\n" % (video))
                    #self.write("</video>\n")
                    words.append(word)
                #print `self.words`
                return words
            else:
                return 0
        except:
            return 0
    
    def getNewest(self,timestamp = 0):

        if timestamp: tmp = filter(lambda x: timestamp - x.timestamp < 360 and len(x.word) >3  and len(x.videos),self.words)
        else:   tmp = filter(lambda x: time() - x.timestamp < 360 and len(x.word) >3  and len(x.videos),self.words)
        return tmp
    
    def __repr__(self):
        tmp = []
        for word in self.words:
            tmp.append(word)
        return `tmp`

class VideoChatter(FlashProtocol):

    name = 'videoclient'
    type = 'modem'
    shown_vids = []

    def connectionMade(self):
        self.factory.numProtocols = self.factory.numProtocols+1
        self.service.addVideoclient(self)

    def connectionLost(self,why=None):
        self.factory.numProtocols = self.factory.numProtocols-1
        shown_vids = []
        self.service.removeVideoclient(self)

    def flash_connect(self, params = {}):
        if(params.has_key('type')):
            self.type = params['type'].lower()
        self.sendMessage("login",{"connected":self.factory.numProtocols,"timestamp":time()})  
        self.service.sendConnected(self.factory.numProtocols)    
        self.flash_getMovie()

    def flash_getMovie(self,params = {}):    
        if params.has_key('time'): timestamp =float(params['time'])
        else: timestamp = 0
        self.service.videolist.getVideo(self,timestamp=timestamp)
        
    def sendMovie(self,videolist,participant,group,timestamp):
        xmlMsg = ""
        #print self.type
        for word,videos in videolist.items():
            videos = filter(lambda video:video.lower().find(self.type)>0,videos)
            videos = filter(lambda video:video not in self.shown_vids,videos)
            if not videos: break
            
            if len(videos)>5: videos = videos[:5]
            
            if len(self.shown_vids)>400: self.shown_vids = self.shown_vids[20:]
            self.shown_vids += videos
            
            xmlMsg += '<videos word="%s" group="%s" user="%s" time="%f">' % (word,group,participant,timestamp)
            for video in videos:
                xmlMsg += '<video src="%s" />' % (video)
            xmlMsg += "</videos>"
        try:
            self.sendLine(xmlMsg)
        except:
            pass
        
        
    def receiveDirectCommand(self, *args, **kw):
        if not args: return
        try:
            apply(self.sendMessage,args,kw)
        except:
            raise CommandNotFound,args

class VideoFactory(Factory):
        
    def __init__(self, service,host,port):
        self.numProtocols  = 0
        self.service = service
        self.host, self.port = host, port
        
    def buildProtocol(self, connection,bot=0):
        i = VideoChatter()
        i.service = self.service
        i.factory = self
        return i

class SimplePerspective(pb.Perspective):
    
    def perspective_addWord(self,words,part,group):
        # i get a wordlist  try to figure out which word is the best
        # and add that 
        return self.service.videolist.add(words,part,group)

    def perspective_getVideo(self,words):
        # i get a wordlist  try to get some vids matching
        return self.service.videolist.getVideo(words)

class SimpleService(pb.Service):
    
    def __init__(self, serviceName, serviceParent=None, authorizer=None, application=None):
        lock = 0
        dbpool = myConnectionPool("MySQLdb", db='unmovie',host='localhost',user='******',passwd='*******')
        self.db = VideoDatabase(dbpool) 
        self.videolist = Videolist()
        self.videolist.service = self
        self.videoclients = []
        pb.Service.__init__(self, serviceName, serviceParent, authorizer, application)
    
    def addVideoclient(self,client):
        if client not in self.videoclients:
            self.videoclients.append(client)
            
    def removeVideoclient(self,client):
        i = 0
        while i<len(self.videoclients)-1:
            i += 1
            if self.videoclients[i] == client:
                del self.videoclients[i]
                break
                
    def sendConnected(self,howmany):
        for client in self.videoclients:
            client.sendLine('<connected num="%d" />' % howmany)
  
    
    def sendClients(self,videolist,participant,group,timestamp):
        for client in self.videoclients:
            client.sendMovie(videolist,participant,group,timestamp)

def quit():
    print "Quitting"
    appl.stop()


def main():
    import video_server
    # run main event loop here
    from twisted.internet import app
    from twisted.cred.authorizer import DefaultAuthorizer
    from twisted.manhole.telnet import ShellFactory


    appl = app.Application("videoserver")
    auth = DefaultAuthorizer(appl)

    svr = video_server.SimpleService("video_server",appl,auth)
        
    svr.perspectiveClass = video_server.SimplePerspective

    p1 = svr.createPerspective("video")

    i1 = auth.createIdentity("video")
    i1.setPassword("hola")
    i1.addKeyByString("video_server", "video")
    auth.addIdentity(i1)


    fls = video_server.VideoFactory(svr,"*******","8789")
    
    sf = ShellFactory()
    sf.username = 'axel'
    sf.password = '8shi'
    sf.namespace['server'] = svr
    sf.namespace['quit'] = video_server.quit

    appl.listenTCP(8790, sf)
    appl.listenTCP(8789,fls)
    appl.listenTCP(8788, pb.BrokerFactory(pb.AuthRoot(auth)))
    appl.run()

if __name__ == '__main__':
    main()
    
    
