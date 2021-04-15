const { EosEvmApi } = require('eos-evm-js')
const { TelosEvmApi } = require("@telosnetwork/telosevm-js");
const fetch = require('node-fetch')

const evmContractAccount = 'eosio.evm'
const SYSTEM_SYMBOL = 'TLOS'

const api = new EosEvmApi({
  endpoint: 'http://localhost:8888',
  chainId: 41,
  ethPrivateKeys: [
  ],
  eosContract: evmContractAccount,
  eosPrivateKeys: [
    '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',
  ]
})

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

async function main () {
  // Deploy EVM contract to EOSIO (deploys to eosContract provided in new EosEvmApi)
  console.log(`Deploying EVM contract in nodejs`)
  await api.eos.setupEvmContract(`/opt/eosio/bin/contracts/eosio.evm`)
  // wait a couple seconds so hyperion can pick up the ABI
  await new Promise(r => setTimeout(r, 2000));
  console.log(`Setting EVM config`)
  const setGas = await telosApi.telos.transact([{
    account: 'eosio.evm',
    name: 'setgas',
    data: {
        min_price: 120000000000,
        min_cost: '0.0002 TLOS'
    },
    authorization: [{ actor: 'eosio.evm', permission: 'active' }]
}])

  console.log(`Creating EVM account`)
  const create = await telosApi.telos.create({ account: 'evmuser1', data: "foobar"});
  console.log(`Depositing to EVM account`)
  const transfer = await telosApi.telos.transact([{
      account: 'eosio.token',
      name: 'transfer',
      data: {
          from: 'evmuser1',
          to: 'eosio.evm',
          quantity: '10100.0000 TLOS',
          memo: 'Deposit'
      },
      authorization: [{ actor: 'evmuser1', permission: 'active' }]
  }])
  console.log(`Getting sender address`)
  const sender = await telosApi.telos.getEthAccountByTelosAccount('evmuser1')
      // Address 0xf79b834a37f3143f4a73fc3934edac67fd3a01cd
      // private key "0x8dd3ec4846cecac347a830b758bf7e438c4d9b36a396b189610c90b57a70163d",
  const receiver = '0xf79b834a37f3143f4a73fc3934edac67fd3a01cd';
  console.log(`Transferring to standalone address`)
  const tlosTransfer = await telosApi.transfer({ account: 'evmuser1', sender: sender.address, to: receiver, quantity: `10000.0000 TLOS` })
}

main()