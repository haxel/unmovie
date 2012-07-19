# Part of UNMOVIE
# Copyright (C) 2002 Axel Heide

import megahal,traceback
from twisted.spread import pb

class SimplePerspective(pb.Perspective):
    megahal = None
    text = ""
    
    def perspective_load(self, name):
        if not self.megahal:
            self.megahal = megahal.Megahal()
            self.megahal.load(name)
        
    def perspective_answer(self, text):
        if not self.megahal: self.perspective_error("no megahal")
        else:
           self.text = self.megahal.answer(text)
           return self.text
           
    def perspective_keywords(self, text):
        if not self.megahal: self.perspective_error("no megahal")
        else:
           self.text = self.megahal.keywords(text)
           return self.text

def main():
    import megahal_server
    from twisted.cred.authorizer import DefaultAuthorizer
    import twisted.internet.app

    appl = twisted.internet.app.Application("megahalserver")
    auth = DefaultAuthorizer(appl)
 
    svr = pb.Service("megahalservice",appl,auth)
    
    svr.perspectiveClass = megahal_server.SimplePerspective
 
    p0 = svr.createPerspective("nietzsche")
    i0 = auth.createIdentity("nietzsche")
    i0.setPassword("****")
    i0.addKeyByString("megahalservice", "nietzsche")
    auth.addIdentity(i0)

    p1 = svr.createPerspective("drella")
    i1 = auth.createIdentity("drella")
    i1.setPassword("****")
    i1.addKeyByString("megahalservice", "drella")
    auth.addIdentity(i1)

    p2 = svr.createPerspective("dylan")
    i2 = auth.createIdentity("dylan")
    i2.setPassword("****")
    i2.addKeyByString("megahalservice", "dylan")
    auth.addIdentity(i2)

    p3 = svr.createPerspective("dogen")
    i3 = auth.createIdentity("dogen")
    i3.setPassword("****")
    i3.addKeyByString("megahalservice", "dogen")
    auth.addIdentity(i3)

    p4 = svr.createPerspective("tark")
    i4 = auth.createIdentity("tark")
    i4.setPassword("****")
    i4.addKeyByString("megahalservice", "tark")
    auth.addIdentity(i4)

    p5 = svr.createPerspective("geisha")
    i5 = auth.createIdentity("geisha")
    i5.setPassword("****")
    i5.addKeyByString("megahalservice", "geisha")
    auth.addIdentity(i5)

    appl.listenTCP(8787, pb.BrokerFactory(pb.AuthRoot(auth)))
    appl.run()

if __name__ == '__main__':
    main()
