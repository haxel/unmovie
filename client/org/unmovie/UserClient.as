/* 
    Part of UNMOVIE
    Copyright (C) 2002 Axel Heide
*/

import org.unmovie.StageClient;

class org.unmovie.UserClient extends StageClient
{
    
    private var movement_listener:Object;
    private var type_listener:Object;
    private var _status:Number;
    private var hex:Array;

    // das ist die unterklasse zu client und bringt die funktionen für den eigenen User
    // steuerung, etc.. 
    function UserClient(id:String,grid:Array)
    {

        movement_listener = new Object()
        movement_listener.scope = this
        type_listener = new Object();

        name = id;
        _status = 6;
        hex = grid;
        
        movement_listener.onKeyDown = function() {
            if (Key.getCode() == Key.RIGHT) {
                this.scope.move("right");
            } else if (Key.getCode() == Key.LEFT) {
                this.scope.move("left");
            } else if (Key.getCode() == Key.UP) {
                this.scope.move("up");
            } else if (Key.getCode() == Key.DOWN) {
                this.scope.move("down");
            }
        };  
        Key.addListener(movement_listener);
    }

    // wird über den keylistener getriggert und schickt eine Request an den Server
    // in welche richtung sich der user bewegen will
    // achtung, die location die zurückkommt muss nicht unbedingt in der gewünschten Richtung liegen
    // wegen collision detection und out of bounds check auf dem server.

    public function move(direction:String):Void
    {
        ring._visible = true
        if (_status != 4) {
            _root.myXML.send('<status user=\"'+_root.userID+'\" mode=\"4\" />');
            _status = 4;
        }
        switch (direction) {
            case "left" :
                desired[0] =  _x - hex[0];
                desired[1] =  _y;
                _root.myXML.send("<move direction='(-1,0)' user='"+_root.userID+"' />");
            break;
            case "right" :
                desired[0] = _x + hex[0];
                desired[1] = _y;
                _root.myXML.send("<move direction='(1,0)' user='"+_root.userID+"' />");
            break;
            case "up" :
                desired[0] = _x;
                desired[1] = _y  - hex[1];
                _root.myXML.send("<move direction='(0,-1)' user='"+_root.userID+"' />");
            break;
            case "down" :
                desired[0] = _x ;
                desired[1] = _y + hex[1];
                _root.myXML.send("<move direction='(0,1)' user='"+_root.userID+"' />");
            break;
        }
        Key.removeListener(movement_listener)
        clearInterval(interval)
        interval = setInterval( this, "startmoving",20);
    };

    public function remove() {
        Key.removeListener(movement_listener)
        //hide_messagebox();
        super.remove();
    };

    public function setup(mode:String):Void 
    {
        _x = 200;
        _y = 200;
        //hide_messagebox();
        super.setup(mode);
        //_root.me = this;    
    };

    public function send(msg:String) 
    {
        showtext(msg)
        _root.showtext("<b><font color='#000000'>" + msg + "</font></b>")
        _root.myXML.send("<msg text='"+msg+"' />");
    };


}
