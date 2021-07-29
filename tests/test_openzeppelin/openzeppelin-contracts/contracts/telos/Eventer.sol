pragma solidity ^0.8.0;

contract Eventer {

    event AnEvent(uint256 indexed val);
    event AnBiggerEvent(uint256 indexed val, bool indexed boo);

    constructor() {
    }

    function doevent(uint256 val) external {
        emit AnEvent(val);
    }

    function dobiggerevent(uint256 val, bool boo) external {
        emit AnBiggerEvent(val, boo);
    }

}