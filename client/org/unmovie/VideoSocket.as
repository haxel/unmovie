/* 
    Part of UNMOVIE
    Copyright (C) 2002 Axel Heide
*/

import mx.events.EventDispatcher;

class org.unmovie.VideoSocket extends XMLSocket
{

    private var connected:Boolean;
    private var checkError:Number;
    private var checkReboot:Number;


    public function VideoSocket()
    {
        EventDispatcher.initialize(this);
        checkError = setInterval(this, "errorCheck", 20*1000);
    }

    function dispatchEvent() {};
    function addEventListener() {};
    function removeEventListener() {};

    public function onConnect(success:Boolean):Void
    {
        if (success)  connected = true;
        else  connected = false;
        dispatchEvent({target:this,type:'connect',success:Boolean(success)});
    }
    
    public function onGetMovie(evt:Object):Void
    {
        send("<getMovie time='"+evt.time+"' />");
    }
    
    public function onClose():Void
    {
        connected = false;
        clearInterval(checkError);
        checkReboot = setInterval(this,"rebootCheck",30 * 1000)
    }

    public function debug(str:String):Void
    {
        var dump:String = str.toString();
        trace( ">>"+dump+"<<");
    }

    public function sendString(msg:String):Void
    {
        var messageObj:XML = new XML();
        messageObj.parseXML(msg);
        send(messageObj);
    }

    public function login(bandwith:String):Void
    {
        sendString('<connect user=\"video\" type=\"'+bandwith+'\" />');
    }

    public function onXML(messageObj:XML):Void
    {
        debug(messageObj.toString());
        var attr:Object = messageObj.firstChild.attributes;
        var name:String = messageObj.firstChild.nodeName;
        switch(name){
            case "login":
                dispatchEvent({target:this,type:'login',error:Boolean(false),presenting_time:String(attr.timestamp)});
            break;
            case "error":
                dispatchEvent({target:this,type:'login',error:Boolean(true),error_text:String(attr.text)});
            break;
            case "connected":
                dispatchEvent({target:this,type:'updateUser',connectedUsers:Number(attr.num)});
            break;
            case "videos":
                var videolist:Array = new Array();
                for (var x:Number=0; x<messageObj.firstChild.childNodes.length; x++) {
                    var video:String = messageObj.firstChild.childNodes[x].attributes.src;
                    videolist.push(Array(video,attr.user,attr.group,attr.word,attr.time));
                }
                dispatchEvent({target:this,type:'fetchedVideos',videos:videolist});
            break;
        }
    }
    
    private function errorCheck():Void
    {
        if(connected == true){
            trace("checking for errors");
        } else {
            if(!checkReboot){
                trace('i am not connected')
                checkReboot = setInterval(this,"rebootCheck",30 * 1000)
            }
        }
        dispatchEvent({target:this,type:'watchdog'});
    }

    private function rebootCheck():Void
    {
        dispatchEvent({target:this,type:'reboot'});
        trace('reboot triggered')
        clearInterval(checkReboot)
        close()
    }
}
