const HDWalletProvider = require("@truffle/hdwallet-provider");

module.exports = {
  contracts_build_directory: './build',
  networks: {
    private: {
      provider: () => new HDWalletProvider(['0x8dd3ec4846cecac347a830b758bf7e438c4d9b36a396b189610c90b57a70163d', '0x18dd1dcd752466afa3d1fac1424333c6461c3a0f1d6702e9c45bc9254ec74e5f', '0x2cf5231887591853fa5dbafa548281962da0419db7f1f4a12817b19fa9ad97c7'], 'https://testnet.telos.net/evm'),
      gas: 10000000,
      gasPrice: 120000000000,
      network_id: '41',
      from: '0xf79b834a37f3143f4a73fc3934edac67fd3a01cd'
    },
  },
  compilers: {
    solc: {
      version: "0.7.6",
    }
  }
}
