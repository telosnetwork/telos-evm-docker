const { BN, expectRevert, expectEvent } = require('@openzeppelin/test-helpers');
const { expect } = require("chai");

const Eventer = artifacts.require("Eventer");
const expectedAnEventBloom = "0x00000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000040000000000000000000000000000000000000000000000100000000000000004000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000";

contract("Eventer", function (accounts) {

  context("Event it!", function () {
    beforeEach(async function () {

      this.eventer = await Eventer.new();
    });

    it("emits an event", async function () {
      const val = 12345;
      const receipt = await this.eventer.doevent(val);
      expectEvent(receipt, 'AnEvent', { val: new BN(val) });
    });


    it("emits an bigger event", async function () {
      const val = 12345;
      const receipt = await this.eventer.dobiggerevent(val, true);
      expectEvent(receipt, 'AnBiggerEvent', { val: new BN(val), boo: true });
    });
  });

});