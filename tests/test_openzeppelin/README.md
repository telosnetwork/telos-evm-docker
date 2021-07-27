<!-- ```git clone https://github.com/OpenZeppelin/openzeppelin-contracts.git ```
```cd openzeppelin-contracts``` -->
```npm install```

```npm audit fix```

<!-- replace the default "hardhat.config.js" with the "hardhat.config.js" in the test_openzeppelin folder -->

```npm run test```

Inside the @openzeppelin test-helper package go to the send.js file and update the gas price such that

```function ether (from, to, value) {
  return web3.eth.sendTransaction({ from, to, value, gasPrice: 120000000000 });
}```

ERC1820 contracts will fails since the raw signed transaction uses 100 gwei instead of 120 gwei,
in the testhelpers/singelton.js change the '0x0' such that
```
 if ((await web3.eth.getCode(ERC1820_REGISTRY_ADDRESS)).length > '0x0000'.length) {
    return getDeployedERC1820Registry();
  }
```