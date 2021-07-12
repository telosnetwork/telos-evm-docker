const { BN, constants, expectEvent, expectRevert } = require('@openzeppelin/test-helpers');
const { expect } = require('chai');

const ERC20Mock = artifacts.require('ERC20Mock');
const ERC20DecimalsMock = artifacts.require('ERC20DecimalsMock');

contract('ERC20 Spammer', function (accounts) {
  const name = 'My Token';
  const symbol = 'MTKN';

  const initialSupply = new BN(1000000);
  const [ initialHolder, ...otherAccounts ] = accounts;

  it('spam', async function () {
    let token = await ERC20Mock.new(name, symbol, initialHolder, initialSupply);

    for await (const account of otherAccounts) {
      await token.transferInternal(initialHolder, account, new BN(1000), { from: initialHolder });
      console.log(`Transferred from ${initialHolder} to ${account}`)
    }

    console.log(`Starting promises`)
    let count = 0;
    let erc20Token = this.token;
    await Promise.all(otherAccounts.map(async (account) => {
      let thisOne = ++count
      console.log(`Starting transfer ${thisOne}`)
      let receipt = await token.transferInternal(account, initialHolder, new BN(1), { from: account });
      expectEvent(receipt, 'Transfer', { from: account, to: initialHolder, value: '1' });

      console.log(`Finished transfer ${thisOne}`)
    }));
    console.log(`Done with promises`)
  });
});
