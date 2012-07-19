/* 
    Part of UNMOVIE
    Copyright (C) 2002 Axel Heide
*/

class org.unmovie.StageClient extends MovieClip
{

    public var name:String;

    private var timeout:Number;
    private var desired:Array;
    private var interval:Number;
    private var depth:Number;

    private var speed:Number;
    private var sound:Sound;
    private var ring:MovieClip;
    private var brain_text:MovieClip;
    private var brain_image:MovieClip;

    private var colorize:Color;

    static var scale:Array;
    static var availZ:Array = new Array(1, 2, 3, 4, 5, 6, 7, 8, 9, 10);
    static var availColors:Array = new Array("0xFF0000", "0xFF3300", "0xFF6600", "0xFF0000", "0xFFAAFF", "0xFFCC00", "0xFFFF00", "0xFFFF33", "0xFFFF66");
    static var availStati:Array = new Array("Offline", "Online", "Away", "avoiding conversation", "searching conversation", "talking", "listening");

    public function StageClient(id:String,scale_factor:Array) {
        name = id;
        timeout = 0;
        interval = 0;
        desired = new Array(0,0);
        speed = 100;
        ring._visible = false;
        scale = scale_factor;
        sound = new Sound(this);
        sound.onLoad = function() {
            this.start();
            this.setVolume(30); 
        }
        brain_text.interval = 0;
        brain_text.show_text = function (msg){
            //trace("gotit_1")
            this.incoming = msg 
            this._visible = true
            this._xscale = 40
            this._yscale = 40
            this.interval = setInterval(this,"fade_in",20)
        }
        
        brain_text.fade_in = function()
        {
            //trace("gotit")
            if(this._xscale < 300){
                this._xscale+=5
                this._yscale+=5
            } else {
                this._visible = false
                clearInterval(this.interval)
            }
        }
    }

    // bringt den bot auf die Bühne
    public function setup(mode:String):Void 
    {
        trace(StageClient.availZ.shift())
        depth = 1
        switch(mode){
            case "cloudy":
                this.attachMovie("botperson", "mc_"+name,depth);
            break;
            default:
                this.attachMovie("botperson_simple", "mc_"+name,depth);
            break;
        }
        colorize = new Color(brain_image);
    };

    // holt den Bot von der Bühne
    // achtung: wenn der mc hier entsorgt wird, muss auch die Instanz entsorgt werden
    // siehe _root.removeUser(userID)
    public function remove():Void 
    {
        clearInterval(interval)
        clearInterval(timeout)
        this.removeMovieClip();
        StageClient.availZ.push(depth)
    };
    // die gewünschte location wird in desired gespeichert und die startmoving funktion
    // mittels Interval in der gewünschten Geschwindigkeit ausgeführt.
    // kann man mit this.spped schneller/langsamer machen
    public function handleLocation(x:Number,y:Number):Void
    {
        trace("[" + desired[0] + "] [" + x/scale[0] + "]")
        desired[0] = x/scale[0];
        desired[1] = y/scale[1];

        stopmoving();
        interval = setInterval( this, "startmoving",speed);
    };
    
    // zeigt die usermessage an. die animation/vergrößerung wird im mc gehandelt
    // siehe botmc in der Library. mittels interval wird nach einer auf der länge 
    // der message basierenden Zeit dier Text ausgeblendet
    public function showtext(msg:String):Void {
        var msecs:Number = msg.length*300 + 1000;
        var z = 1;
        timeout = setInterval(this, "hidetext", msecs);
        brain_text.incoming.html = true;
        //this.mc.brain_text.incoming = msg;
        brain_text.show_text(msg)
        brain_text._visible = true;
        sound.loadSound("http://193.197.170.79/cgi-bin/mbrola.pl?text="+ msg +"&emotion="+z, true);
    };

    // blendet message text aus
    public function hidetext():Void
    {
        clearInterval(timeout);
        brain_text._visible = false;
    };

    // sorgt für die Bewegung der Bots. sehr simpel 1 pixel pro zeiteinheit this.speed
    public function startmoving():Void
    {
        //trace(this.desired[0]+ ":" + this.desired[1])
        //trace(this.mc._x+ ":" + this.mc._y)
    
        if(Math.abs(desired[0]-_x) > 2 || Math.abs(desired[1]-_y) > 2){
            if(_x > desired[0]) _x = _x - 2;
            else if(_x < desired[0]) _x = _x + 2;

            if(_y > desired[1]) _y = _y - 2;
            else if(_y < desired[1]) _y = _y + 2;

            _y = Math.ceil(_y)
            _x = Math.ceil(_x)
            //this.interval = setInterval( this, "startmoving",2);    
        }else{                
            stopmoving();
            // Key.addListener(this.movement_listener);
        }
    };


    public function setLocation(x:Number,y:Number):Void
    {
        stopmoving();
        _x = x
        _y = y
    };

    public function setStatus(mode:Number):Void
    {
        colorize.setRGB(StageClient.availColors[mode]);
        StageClient.availStati[mode];
    };

    // beendet bewegung
    public function stopmoving():Boolean
    {
        ring._visible = false
        clearInterval(interval);
        return true;
    };
    



}