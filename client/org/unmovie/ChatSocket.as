/* 
    Part of UNMOVIE
    Copyright (C) 2002 Axel Heide
*/

import org.unmovie.Log
import mx.events.EventDispatcher;

class org.unmovie.ChatSocket extends XMLSocket
{
        
    private var connected:Boolean;    
    private var _host:String;
    private var log:Log;
    private var _port:Number;

    public function ChatSocket()
    {
        log = Log.getInstance(); 
        EventDispatcher.initialize(this);
    }

    function dispatchEvent() {};
    function addEventListener() {};
    function removeEventListener() {};

    function connect(url:String,port:Number):Boolean
    {
        _host = url;
        _port = port;
        return super.connect(url,port);
    }

    public function onConnect(success:Boolean):Void
    {
        if (success)  connected = true;
        else  connected = false;
        dispatchEvent({target:this,type:'connect',success:Boolean(success)});
    }

    public function onClose():Void
    {
        connected = false;
        dispatchEvent({target:this,type:'close'});
        // clearInterval(checkError);
        // checkReboot = setInterval(this,"rebootCheck",30 * 1000)
    }

    public function onXML(messageObj:XML):Void
    {

        var attributes = messageObj.firstChild.attributes;
        var name = messageObj.firstChild.nodeName;
        var sender = messageObj.firstChild.attributes.sender;
        switch(name){

            case "login":
                dispatchEvent({target:this,type:'onLogin',user:attributes.user});
                break;
                
            case "users":
                var user_names:Array = attributes.users.split(":");
                var user_locations:Array = attributes.locations.split(":");
                var user_stati:Array = attributes.statuses.split(":");
                dispatchEvent({target:this,type:'onUsers',users:user_names,locations:user_locations,stati:user_stati});
                break;
                
            case "status":
                dispatchEvent({target:this,type:'onStatus',mode:attributes.mode,sender:attributes.sender});
                break;
        
            case "msg":
                dispatchEvent({target:this,type:'onMessage',message:attributes.text,sender:attributes.sender});
                break;
                
            case "botmsg":
                dispatchEvent({target:this,type:'onMessage',message:attributes.text,sender:attributes.sender});                
                break;
                
            case "botkeys":
                dispatchEvent({target:this,type:'onKeys',message:attributes.text,sender:attributes.sender});                
                break;
                
            case "group":
                dispatchEvent({target:this,type:'onGroup',members:attributes.members.split(";")});                
                break;
        
            case "location":
                dispatchEvent({target:this,type:'onLocation',sender:attributes.sender,x:attributes.x,y:attributes.y});                
                break;
    
            case "error":
                dispatchEvent({target:this,type:'onError',error:attributes.text});                
                break;
        }
    }

    public function sendString(msg:String):Void
    {
        var messageObj:XML = new XML();
        messageObj.parseXML(msg);
        send(messageObj);
    }


    public function sendLogin(user:String,x:Number,y:Number):Void
    {
        sendString('<connect user=\"'+user+'\" location=\"('+x+','+y+')\" />');
    };

    public function quit() {
        trace('quit damnit')
        if (connected) {
            close();
            dispatchEvent({target:this,type:'onQuit'});
        }
    }
}
