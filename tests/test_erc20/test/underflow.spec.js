let token;

const ERC20 = artifacts.require("ERC20");

contract("ERC20", (accounts) => {
  const tokenName = "El Oh El Token";
  const tokenSymbol = "LOL";
  const tokenDecimals = 4;
  const numTokensCreated = 10000;

  beforeEach(async () => {
    token = await ERC20.new(
      numTokensCreated,
      tokenName,
      tokenDecimals,
      tokenSymbol,
      {
        from: accounts[0],
      }
    );
    // console.log("deployed address:" + token.address);
  });

  it("bugtest: testing underflow, sending all base tokens (might need to restart containers)", async () => {
    // Go into Settings > Advanced > Reset account on metamask when testing there
    const balance0_beforesend = await web3.eth.getBalance(accounts[1]);
    const balance1_before = await web3.eth.getBalance(accounts[2]);
    console.log(
      `Acc0 before: ${web3.utils.fromWei(balance0_beforesend, "Ether")}`
    );
    console.log(
      `Acc1 before: ${web3.utils.fromWei(balance1_before, "Ether")}`
    );
    let gasPrice = "120000000000";
    let gas = "21000";
    let gasWei = web3.utils.toBN(gasPrice).mul(
      web3.utils.toBN(gas)
    );
    console.log(`Gas: ${web3.utils.fromWei(`${gasWei}`, "Ether")}`);

    // deduct from balance
    let sendAmount = web3.utils.toBN(balance0_beforesend).sub(
      web3.utils.toBN(gasWei)
    );
    // let sendAmount = web3.utils.toWei("1", "ether");
    console.log(`Sending: ${web3.utils.fromWei(`${sendAmount}`, "Ether")}`);

    let threw = false;
    try {
      await web3.eth
        .sendTransaction({
          from: accounts[1],
          to: accounts[2],
          value: `${sendAmount}`,
          gas: gas,
          gasPrice: gasPrice,
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

    const balance0_aftersend = await web3.eth.getBalance(accounts[1]);
    const balance1_aftersend = await web3.eth.getBalance(accounts[2]);
    console.log(
      `Acc0 after: ${web3.utils.fromWei(balance0_aftersend, "ether")}`
    );
    console.log(
      `Acc1 after: ${web3.utils.fromWei(balance1_aftersend, "ether")}`
    );

    let difference = web3.utils.toBN(balance0_beforesend).sub(
      web3.utils.toBN(balance0_aftersend)
    );
    console.log(`Difference: ${web3.utils.fromWei(`${difference}`, "ether")}`);
    // let gasUsed = difference.sub(web3.utils.toBN(sendAmount));
    // console.log(`Gas used: ${web3.utils.fromWei(`${gasUsed}`, "ether")}`);

    // transaction completed
    assert.strictEqual(threw, false)

    // owner balance less than before
    assert.isTrue(web3.utils.toBN(balance0_aftersend).lt(web3.utils.toBN(balance0_beforesend)), `${web3.utils.toBN(balance0_aftersend).toString()} Overflow`)

    // amount sent correct
    a = web3.utils.toBN(sendAmount);
    b = web3.utils.toBN(balance1_before);
    assert.strictEqual(web3.utils.toBN(balance1_aftersend).toString(), a.add(b).toString())
  });
});
