export default class debugLogger {
    /**
    * Adds an element to a bit vector of a 64 byte bloom filter.
    * @param s - The string to console log
    * @param b - The boolean conditional to print logs
    */
    log(s: string, b: boolean) {
        if (b == true) {
            console.log(s);
        }
    }
}
