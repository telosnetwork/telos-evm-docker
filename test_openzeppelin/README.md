<!-- ```git clone https://github.com/OpenZeppelin/openzeppelin-contracts.git ```
```cd openzeppelin-contracts``` -->
```npm install```

```npm audit fix```

<!-- replace the default "hardhat.config.js" with the "hardhat.config.js" in the test_openzeppelin folder -->

```npm run test```

Inside the @openzeppelin test-helper package go to the send.js file and update the gas price such that

```
function ether (from, to, value) {
  return web3.eth.sendTransaction({ from, to, value, gasPrice: 120000000000 });
}
```
