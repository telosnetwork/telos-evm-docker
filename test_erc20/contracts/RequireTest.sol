// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

contract RequireTest{

    event Failure(uint expectedInt , uint givenInt);
    
    function requireWithMessage(uint myInt) public returns(bool){ 
        require (myInt >= 5);
        emit Failure(5, myInt);
        return true;
    }

    function requireWithOutMessage(uint myInt) public  returns(bool)  {
        require (myInt >= 5,"This require has a messages");
        emit Failure(5, myInt);
        return true;
    }
}