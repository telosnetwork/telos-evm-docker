const { TelosEvmApi } = require("./node_modules/@telosnetwork/telosevm-js/lib/cjs/telosevm-js.js");
const fetch = require('node-fetch')

const evmContractAccount = 'eosio.evm'

const telosApi = new TelosEvmApi({
    // Ensure the API has console printing enabled
    endpoint: "http://localhost:8888",

    // Must match the chain ID the contract is compiled with (1 by default)
    chainId: 41,

    ethPrivateKeys: [
        // Public Key: 0xf79b834a37f3143f4a73fc3934edac67fd3a01cd
        "0x8dd3ec4846cecac347a830b758bf7e438c4d9b36a396b189610c90b57a70163d",
    ],

    telosContract: evmContractAccount,
    fetch,
    telosPrivateKeys: [
        '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',
    ],
});

telosApi.setDebug(true);
async function main () {
    const sender = await telosApi.telos.getEthAccountByTelosAccount('evmuser1')
    const receiver = '0xf79b834a37f3143f4a73fc3934edac67fd3a01cd';

    const tlosTransfer = await telosApi.transfer({
        account: 'evmuser1',
        sender: sender.address, to: receiver,
        quantity: `100000000.0000 TLOS`
    })
    const tlosTransfer1 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0xc51fE232a0153F1F44572369Cefe7b90f2BA08a5', quantity: `100000.0000 TLOS` })
    const tlosTransfer2 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0xf922CC0c6CA8Cdbf5330A295a11A40911FDD3B6e', quantity: `10000.0000 TLOS` })
    const tlosTransfer3 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0xCfCf671eBE5880d2D7798d06Ff7fFBa9bdA1bE64', quantity: `10000.0000 TLOS` })
    const tlosTransfer4 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0xf6E6c4A9Ca3422C2e4F21859790226DC6179364d', quantity: `10000.0000 TLOS` })
    const tlosTransfer5 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0xe83b5B17AfedDb1f6FF08805CE9A4d5eDc547Fa2', quantity: `10000.0000 TLOS` })
    const tlosTransfer6 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0x97baF2200Bf3053cc568AA278a55445059dF2d97', quantity: `10000.0000 TLOS` })
    const tlosTransfer7 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0x2e5A2c606a5d3244A0E8A4C4541Dfa2Ec0bb0a76', quantity: `10000.0000 TLOS` })
    const tlosTransfer8 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0xb4A541e669D73454e37627CdE2229Ad208d19ebF', quantity: `10000.0000 TLOS` })
    const tlosTransfer9 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0x717230bA327FE8DF1E61434D99744E4aDeFC53a0', quantity: `10000.0000 TLOS` })
    const tlosTransfer10 = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: '0x52b7c04839506427620A2B759c9d729BE0d4d126', quantity: `10000.0000 TLOS` })
}

main()
