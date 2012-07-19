/* 
    Part of UNMOVIE
    Copyright (C) 2002 Axel Heide
*/

import org.unmovie.ChatSocket;
import org.unmovie.StageClient;
import org.unmovie.UserClient;
import org.unmovie.Log;
import mx.utils.Delegate;

class org.unmovie.ChatController
{
    private static var inst:ChatController;

    private var users:Array;
    private var group:Array;
    private var username:String;
    private var log:Log;
    private var socket:ChatSocket;

    private function ChatController() {
        log = Log.getInstance(); 
    }

    public static function getInstance():ChatController {
        if (inst == null) inst = new ChatController();
        return inst;
     }

    public function connect(new_host:String,new_port:Number):ChatSocket {
        log.trace("connect to chat ...")
        socket = new ChatSocket();   
        socket.connect(new_host,new_port)
        return socket;
    }

    public function getSocket():ChatSocket
    {
        return socket;
    }

    
    public function login(user:String):Void
    {
        log.trace("login to chat ...")
        var startx = int(Math.random() * 768)
        var starty = int(Math.random() * 576)
        socket.sendLogin(user,startx,starty);
        username = user;
    }

    public function onUsers(evt:Object)
    {        
        for (var i = 0; i<evt.users.length; i++) {
            if (!users[evt.users[i]]) {
                var user = addUser(evt.users[i]);
                var x_y = new Array();
                x_y = evt.locations[i].split(",");
                user.setLocation(x_y[0],x_y[1]);
                //user.setStatus(users_statuses[i])
               //this.debug(uid);
                // _root.myXML.send('<status user=\"'+convertTags(user)+'\" mode=\"6\" />');
            }
        }
    }

    public function onStatus(evt:Object)
    {
        var user = users[evt.sender];
        user.setStatus(evt.mode);
        removeFromGroup(evt.sender);
        if(evt.mode==0){
            removeUser(users[evt.sender]);
        }
    }
 
    public function onGroup(evt:Object)
    {
        var members = evt.members;
        for(var member in members){
            if(members[member] == users[username]){
                addToGroup(members)
                users[username].stopmoving();
                //trace(Key.removeListener(this.getUserObj(_root.userID)))
            }
        }        
    }

    public function removeUser(user:String)
    {
    }

    public function addUser(user:String):StageClient
    {
        if(user==""||users[user]) return;

        if (username == user) var user_mc:UserClient = new UserClient(user);
        else var user_mc:StageClient = new StageClient(user);

        users.push(user_mc);
        user_mc.setup();
        return user_mc;
    }


    public function leaveGroup()
    {
        _root.myXML.send("<status mode='4' />");
        //hide_messagebox();
        group = new Array();
        //Key.addListener(this);
    };

    // das ist noch etwas buggy. hier sammel ich welche user in meiner diskussionsgruppe sind.
    // um z.b das textfield einzublenden
    public function addToGroup(members:Array):Boolean
    {
        for (var i = 0; i<members.length; i++) {
            if(username == members[i]){
                if(members.length == 1) {
                    group = new Array();
                    //hide_messagebox();
                } else {
                    trace("show")
                    //show_messagebox();
                }
            } else {
                for (var j= 0; j<group.length;j++) {
                    if(group[j] == members[i]){
                        return true;
                    }
                }
                group.push(members[i]);
            }
        }
        return true;
    }

    public function removeFromGroup(sender:String) {
        for (var i = 0; i<group.length; i++) {
            if(group[i] == sender && sender == 3)
                delete group[i]
        }
        //if (group.length == 0) hide_messagebox();
    }


}