const Aimp = artifacts.require('A.sol');
const Bimp = artifacts.require('B.sol');
const Gimp = artifacts.require('G.sol');

contract('Trace', accounts => {
  const [owner, ...others] = accounts;

  beforeEach(async () => {
    G = await Gimp.new();
    F = await Bimp.new(G.address);
    D = await Bimp.new(G.address);
    C = await Bimp.new(F.address);
    B = await Bimp.new(G.address);
    A = await Aimp.new();
    console.log(G.address)
    console.log(F.address)
    console.log(D.address)
    console.log(C.address)
    console.log(B.address)
    console.log(A.address)
  });


  describe('#saveValue()', () => {
    it('should successfully save value', async () => {
      await A.setValue(B.address, C.address, D.address, 108, { from: others[0]});
      const valueBefore = await G.val(); 	
      assert(valueBefore.toString() === '111');
    });
  });
});


