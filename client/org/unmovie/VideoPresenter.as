/* 
    Part of UNMOVIE
    Copyright (C) 2002 Axel Heide
*/

import mx.events.EventDispatcher;

class org.unmovie.VideoPresenter extends MovieClip{


    public var video_liste:Array = new Array();
    private var shownvideos:Array;
    
    public var vid_playing:String;
    public var vid_url:String;
    public var vid_bandwidth:String;

    public var word_mc:MovieClip;
    public var video_mc:MovieClip;
    public var pause:MovieClip;
    public var error_txt:TextField;
    
    private var streamer:Number;
    private var _position:Number;


    private var presenting_time:String;
    private var last_word:String;

    public function VideoPresenter()
    {
        EventDispatcher.initialize(this);
        
        word_mc.presenting = false;
        video_mc.presenting = false;
        video_mc.timebar._xscale = 0;
        last_word = "";
        shownvideos = new Array();
    }

    public function setProperties(n_url:String,n_bandwidth:String):Void
    {
        vid_url = n_url;
        vid_bandwidth = n_bandwidth;
    }

    public function onConnect(evt:Object):Void
    {
        trace(" .. " + evt.success);
        if(evt.success){
            gotoAndStop("login")
        }
    }

    public function onLogin(evt:Object):Void
    {
        if(evt.error){
            gotoAndStop("error");
            error_txt.text = evt.error_text;
        } else {
            gotoAndStop("loggedIn");
            startStreaming(evt.presenting_time)
        }
    }

    function onReboot(){
        gotoAndStop(1);
    }
   
    public function onEnterFrame():Void
    {

        // nach 50 Frames ausblenden
        if(word_mc.presenting == true && word_mc.framecount < 50){
            word_mc._visible = true;
            word_mc.framecount++;
        } else {
            word_mc._visible = false;
            word_mc.framecount = 0;
            word_mc.presenting = false;
        }

        // video abspielen
        if (video_mc.presenting) {
        
            var f:Number = video_mc.video._framesloaded;
            var t:Number = video_mc.video._totalframes;
            var c:Number = video_mc.video._currentframe;
            var percentage:Number = c/t;
            

            if(!(t == 1 && f == 1 && c==1)){
                video_mc.timebar._xscale = percentage*100;
                if (percentage and percentage*100>=90) {
                    video_mc.presenting = false;
                    //this.timebar.swapDepths(this.video);
                    // video_mc.video.unloadMovie()
                    trace("movie unloaded")
                    vid_playing = "";
                    show_vids();
                }
            } else {
                video_mc.timebar._xscale = 0;
            }
        }
    }

    public function onAddVideos(evt):Void
    {
        if(evt.videos.length>0){
            for(var x = 0;x < evt.videos.length;x++){
                var vid:Object = evt.videos[x];
                video_liste.push(vid);
            }
        }
    }

    public function watchdog()
    {
        if (video_mc.presenting) {
            trace("checking for errors:" + video_mc.video._currentframe);
            if (video_mc.video._totalframes == _position || video_mc.video._currentframe == _position) { // am ende oder bewegt sich nicht
                trace("reset")
                video_mc.presenting = false;
                //video_mc.video.removeMovieClip()
                shownvideos.push(vid_playing)
                vid_playing = "";
                _position = 0;
                get_vid()
            } else {
                trace("set position")
                _position = video_mc.video._currentframe;
            }
        } else {
            trace("checking for errors no vid");
            shownvideos.push(vid_playing)
            vid_playing = "";
            get_vid()
        }
    }

    public function  startStreaming(time:String):Void
    {
        presenting_time = time;
        streamer = setInterval(this,"show_vids",2*1000);
        get_vid();
    }
    function dispatchEvent() {};
    function addEventListener() {};
    function removeEventListener() {};
    

    private function get_vid():Void
    {
        if (video_mc.presenting == false) {
            trace("<getMovie time='"+presenting_time+"' />")
            dispatchEvent({target:this,type:'getMovie',time:String(presenting_time)});
            presenting_time = String(Number(presenting_time) - 1000);
        }
    }

    private function present_word(word:String) {
        trace("presenting word: "+word);
        word_mc.word_txt.text = word;
        word_mc.presenting = true;
    }
    
    private function present_video(video:String, word:String) {

        trace("presenting video: " + video + " word:" +word );
        /*if(!video_mc.video) {
            video_mc.createEmptyMovieClip("video",100);
            video_mc.timebar.swapDepths(101);
        }*/
        var mcl = new MovieClipLoader();
        var mcll = new Object();
        mcll.onLoadComplete = function(target){
            trace(target)
        }
        mcl.addListener(mcll);
        mcl.loadClip(vid_url+video,video_mc.video);
        video_mc.presenting = true;
        vid_playing = video;
        
    }

    private function show_vids():Boolean
    {
        //trace("show_vids triggered" + video_liste.toString());
        if (video_mc.presenting == false) {
            if(video_liste.length==0){
                get_vid();
                return false;
            }
            var video = Array();
            while(1){
                video = video_liste.shift();
                var vid:String = filter_vids(video[0]);
                trace("Video:" + vid);
                if(vid != "") break;
                if(video_liste.length<1){
                    get_vid();
                    return false;
                }
            }
            presenting_time =  video[4]
            
            dispatchEvent({target:this,type:'playing',time:String(presenting_time)});
 
            pause._visible = false;
            present_video(video[0], video[3]);
                    
            if(last_word != video[3]){
                present_word(video[3])
                last_word=video[3]
            }
            return true;
        }
    }
    
    private function filter_vids(vid:String):String
    {
        if (shownvideos.length>0) {
            var i = 0;
            while(1){
                if(shownvideos.length < i){
                    break;
                }
                if (shownvideos[i] == vid) {
                    return "";
                } 
                i++;
            }
        }
        shownvideos.push(vid);
        return vid;
    }

}
