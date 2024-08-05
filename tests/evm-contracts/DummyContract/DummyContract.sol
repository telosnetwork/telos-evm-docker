// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

contract DummyContract {
    uint public number;

    event NumberSet(uint newNumber);

    function setNumber(uint _number) public {
        require(_number > 10, "Number must be greater than 10");

        number = _number;
        emit NumberSet(_number);
    }
}
