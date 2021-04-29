const HDWalletProvider = require("@truffle/hdwallet-provider");

module.exports = {
  contracts_build_directory: './build',
  networks: {
    private: {
      provider: () => new HDWalletProvider([
        '0xc51fE232a0153F1F44572369Cefe7b90f2BA08a5',
        '0xf922CC0c6CA8Cdbf5330A295a11A40911FDD3B6e',
        '0xCfCf671eBE5880d2D7798d06Ff7fFBa9bdA1bE64',
        '0xf6E6c4A9Ca3422C2e4F21859790226DC6179364d',
        '0xe83b5B17AfedDb1f6FF08805CE9A4d5eDc547Fa2',
        '0x97baF2200Bf3053cc568AA278a55445059dF2d97',
        '0x2e5A2c606a5d3244A0E8A4C4541Dfa2Ec0bb0a76',
        '0xb4A541e669D73454e37627CdE2229Ad208d19ebF',
        '0x717230bA327FE8DF1E61434D99744E4aDeFC53a0',
        '0x52b7c04839506427620A2B759c9d729BE0d4d126'
      ], 'http://38.75.136.87:7000/evm'),
      gas: 10000000,
      gasPrice: 120000000000,
      network_id: "41",
      from: '0xf79b834a37f3143f4a73fc3934edac67fd3a01cd'
    },
  },
  compilers: {
    solc: {
      version: "0.7.6",
    }
  }
}
