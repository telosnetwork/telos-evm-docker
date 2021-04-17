# Telos EVM RPC plugin for Hyperion API

Installation on working Hyperion Indexer/Api (v3.3+)

```bash
npm run plugin-manager install telos-evm
```

Required Config on chain.config.json
```json
"plugins": {
  "telos-evm": {
      "enabled": true,
      "chainId": 41,
      "signer_account": "TELOS_ACCOUNT",
      "signer_permission": "active",
      "signer_key": "TELOS_PRIVATE_KEY",
      "contracts": {
        "main": "eosio.evm"
      }
  }
}
```

### Implemented Routes

#### /evm (JSON RPC 2.0)

Methods:
  - eth_accounts
  - eth_blockNumber
  - eth_call
  - eth_chainId
  - eth_estimateGas
  - eth_getBalance
  - eth_getBlockByNumber
  - eth_getBlockByHash
  - eth_getBlockTransactionCountByNumber
  - eth_getBlockTransactionCountByHash
  - eth_getCode
  - eth_getLogs
  - eth_getStorageAt
  - eth_getTransactionCount
  - eth_getTransactionByHash
  - eth_getTransactionReceipt
  - eth_getUncleCountByBlockNumber
  - eth_getUncleCountByBlockHash
  - eth_gasPrice
  - eth_sendTransaction
  - eth_sendRawTransaction
  - net_listening
  - net_version
