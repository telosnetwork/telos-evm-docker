export default class DebugLogger {

    loggingEnabled : boolean;

    constructor(loggingEnabled:boolean){
        if (loggingEnabled) {
            this.loggingEnabled = true;
        }else{
            this.loggingEnabled = false;
        }
    }

    /**
    * Adds an element to a bit vector of a 64 byte bloom filter.
    * @param s - The string to console log
    */
    log(s: string, ) {
        if (this.loggingEnabled == true) {
            console.log(s);
        }
    }
}
