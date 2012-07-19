/* 
    Part of UNMOVIE
    Copyright (C) 2002 Axel Heide
*/

class org.unmovie.Log
{
    private static var inst:Log;

    private function Log() {}

    public static function getInstance():Log {
        if (inst == null) inst = new Log();
        return inst;
     }

    public function trace(msg:String)
    {
        var d = new Date();
        
        trace(d.toString() + ": " + msg);
    }

    public function debug(o:Object)
    {
        for(var p in o) {
            if(typeof(o[p]) == "string") {
                this.trace(p + " -> " + o[p]);
            } else {
                this.trace(p);
                for(var m in o[p]) {
                    trace(" -> " + m);
                }
            }
        }
    }

}