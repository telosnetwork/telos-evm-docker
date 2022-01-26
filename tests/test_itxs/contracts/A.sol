pragma solidity ^0.7.6;
import "./B.sol";

contract A {

    function setValue(address _addr1, address _addr2, address _addr3, uint256 x) public returns (uint256) {
        B b = B(_addr1);
        B c = B(_addr2);
        B d = B(_addr3);
        b.setValue(x);
        c.setValue(x+1);
        d.setValue(x+2);
        return 2;
    }
}
