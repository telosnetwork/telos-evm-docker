require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-web3");

/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
  solidity: "0.7.3",
  defaultNetwork: "private",
  networks: {
    private: {
      url: "http://127.0.0.1:7000/evm",
      gas: 10000000,
      gasPrice: 120000000000,
      accounts: [
        '0x87ef69a835f8cd0c44ab99b7609a20b2ca7f1c8470af4f0e5b44db927d542084',
        '0xe014b35c1921894db39c21dbb33462927ff19d9a43a6e226d2a8c8733cc72c6e',
        '0x13246160959c6a50c4a6ee01b0253d13182c5e8cccc83c7e0894b8af6fdd360b',
        '0xc05100490323a43cae3b509ddb6ae5b55ccd2fb7f3b5747cc6ac722519af359c',
        '0xeac4556bff5331018fff633f5a16b18de9edf4f6ea21e09c4a212721eb371d48',
        '0xd95580e6b27465737103faecd7539c11fbf09f13eca0ac66b651e999b4215d85',
        '0x5ce2e2fded89345e71b99fc9c212438f02049a7c7375df49ae3e93c47249630e',
        '0xb79714ccfda6ec0d0553f31559e4e599a983a1f51b9334e5445dcc734128d5c8',
        '0xccb2775f20f2df9b7c756fe4323ccda06c7bcf81a6dfa2391a38eb58714a2913',
        '0xf051e068357022ee273e6924244007e09f0002ba3902d17e8eb6d2498d829d82'
      ],
    }
  }
};
