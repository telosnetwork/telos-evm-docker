// We import Chai to use its asserting functions here.
const { expect } = require("chai");
const { ethers } = require("hardhat");

// `describe` is a Mocha function that allows you to organize your tests. It's
// not actually needed, but having your tests organized makes debugging them
// easier. All Mocha functions are available in the global scope.

// `describe` receives the name of a section of your test suite, and a callback.
// The callback must define the tests of that section. This callback can't be
// an async function.
describe("Token contract", function () {
  // Mocha has four functions that let you hook into the the test runner's
  // lifecyle. These are: `before`, `beforeEach`, `after`, `afterEach`.

  // They're very useful to setup the environment for tests, and to clean it
  // up after they run.

  // A common pattern is to declare some variables, and assign them in the
  // `before` and `beforeEach` callbacks.

  let Token;
  let hardhatToken;
  let owner;
  let addr1;
  let addr2;
  let addrs;

  // `beforeEach` will run before each test, re-deploying the contract every
  // time. It receives a callback, which can be async.
  beforeEach(async function () {
    // Get the ContractFactory and Signers here.
    Token = await ethers.getContractFactory("Token");
    [owner, addr1, addr2, ...addrs] = await ethers.getSigners();

    // To deploy our contract, we just have to call Token.deploy() and await
    // for it to be deployed(), which happens onces its transaction has been
    // mined.
    hardhatToken = await Token.deploy();
  });

  describe("Transactions", function () {
    it("bugtest: testing underflow, sending all base tokens", async () => {
      // TODO should reset gas TLOS
      // Go into Settings > Advanced > Reset account on metamask when testing there
      const balance0_beforesend = await web3.eth.getBalance(addr1.address);
      const balance1_before = await web3.eth.getBalance(addr2.address);
      console.log(
        `Acc0 before: ${web3.utils.fromWei(balance0_beforesend, "Ether")}`
      );
      let gasPrice = "120000000000";
      let gas = "21000";
      let gasWei = ethers.BigNumber.from(gasPrice).mul(
        ethers.BigNumber.from(gas)
      );
      // console.log(gasWei);
      console.log(`Gas: ${web3.utils.fromWei(`${gasWei}`, "Ether")}`);

      // deduct from balance
      let sendAmount = ethers.BigNumber.from(balance0_beforesend).sub(
        ethers.BigNumber.from(gasWei)
      );
      // let sendAmount = web3.utils.toWei("1", "ether");
      console.log(`Sending: ${web3.utils.fromWei(`${sendAmount}`, "Ether")}`);

      let threw = false;
      try {
        await web3.eth
          .sendTransaction({
            from: addr1.address,
            to: addr2.address,
            value: `${sendAmount}`,
            gas: 21000,
            gasPrice: "120000000000",
          })
          .on("transactionHash", function (hash) {
            console.log(hash);
          })
          // .on("receipt", function (receipt) {
          //   console.log(receipt);
          // })
          .on("error", console.error); // If a out of gas error, the second parameter is the receipt.;
      } catch (e) {
        threw = true;
      }

      const balance0_aftersend = await web3.eth.getBalance(addr1.address);
      const balance1_aftersend = await web3.eth.getBalance(addr2.address);
      console.log(
        `Acc0 after: ${web3.utils.fromWei(balance0_aftersend, "ether")}`
      );
      // console.log(balanceevm_aftersend);

      let difference = ethers.BigNumber.from(balance0_beforesend).sub(
        ethers.BigNumber.from(balance0_aftersend)
      );

      console.log(
        `Difference: ${web3.utils.fromWei(`${difference}`, "ether")}`
      );

      let gasUsed = difference.sub(ethers.BigNumber.from(sendAmount));
      console.log(`Gas used: ${web3.utils.fromWei(`${gasUsed}`, "ether")}`);

      // transaction completed
      expect(threw).to.equal(false);

      // owner balance less than before
      expect(ethers.BigNumber.from(balance0_aftersend)).to.be.lt(
        ethers.BigNumber.from(balance0_beforesend)
      );

      // amount sent correct
      a = ethers.BigNumber.from(sendAmount);
      b = ethers.BigNumber.from(balance1_before);
      expect(ethers.BigNumber.from(balance1_aftersend)).to.equal(a.add(b));
    });
  });
});
