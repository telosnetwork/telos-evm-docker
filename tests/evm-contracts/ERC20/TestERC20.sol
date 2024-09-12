// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

contract TestERC20 is ERC20, ERC20Permit {
    address private _owner;

    constructor(
        address owner,
        string memory name,
        string memory symbol
    ) ERC20(name, symbol) ERC20Permit(name) {
        _owner = owner;
    }

    error UnauthorizedAccount(address account);

    function mint(address to, uint256 amount) public {
        if (_owner != _msgSender()) {
            revert UnauthorizedAccount(_msgSender());
        }
        _mint(to, amount);
    }
}
