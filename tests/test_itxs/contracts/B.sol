pragma solidity ^0.7.6;
import "./G.sol";

contract B {
    address gaddr;

    constructor(address addr) public {
        gaddr = addr;
    }

    function setValue(uint256 x) public returns (address) {
        G g = G(gaddr);
        g.setValue(x);
        g.setValue(x+1);
        return gaddr;
    }
}
