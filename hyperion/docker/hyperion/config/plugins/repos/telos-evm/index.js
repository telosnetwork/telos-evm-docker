"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const hyperion_plugin_1 = require("../../hyperion-plugin");
const node_fetch_1 = __importDefault(require("node-fetch"));
const fastify_autoload_1 = __importDefault(require("fastify-autoload"));
const path_1 = require("path");
const tx_1 = require("@ethereumjs/tx");
const common_1 = __importDefault(require("@ethereumjs/common"));
const bloom_1 = __importDefault(require("./bloom"));
const BN = require('bn.js');
const createKeccakHash = require('keccak');
const { TelosEvmApi } = require('@telosnetwork/telosevm-js');
class TelosEvm extends hyperion_plugin_1.HyperionPlugin {
    constructor(config) {
        super(config);
        this.hasApiRoutes = true;
        this.actionHandlers = [];
        this.deltaHandlers = [];
        this.decimalsBN = new BN('1000000000000000000');
        this.baseChain = 'mainnet';
        this.hardfork = 'istanbul';
        this.counter = 0;
        if (this.baseConfig) {
            this.pluginConfig = this.baseConfig;
            if (config.contracts?.main) {
                this.dynamicContracts.push(config.contracts.main);
            }
            if (config.chainId) {
                this.common = common_1.default.forCustomChain(this.baseChain, { chainId: config.chainId }, this.hardfork);
                this.loadActionHandlers();
                this.loadDeltaHandlers();
            }
        }
    }
    loadDeltaHandlers() {
        // eosio.evm::receipt
        this.deltaHandlers.push({
            table: 'receipt',
            contract: 'eosio.evm',
            mappings: {
                delta: {
                    "@evmReceipt": {
                        "properties": {
                            "index": { "type": "long" },
                            "hash": { "type": "keyword" },
                            "trx_index": { "type": "long" },
                            "block": { "type": "long" },
                            "block_hash": { "type": "keyword" },
                            "trxid": { "type": "keyword" },
                            "status": { "type": "byte" },
                            "epoch": { "type": "long" },
                            "createdaddr": { "type": "keyword" },
                            "gasused": { "type": "long" },
                            "ramused": { "type": "long" },
                            "logs": {
                                "properties": {
                                    "address": { "type": "keyword" },
                                    "data": { "enabled": false },
                                    "topics": { "type": "keyword" }
                                }
                            },
                            "logsBloom": { "type": "keyword" },
                            "output": { "enabled": false },
                            "errors": { "enabled": false },
                            "itxs": {
                                "properties": {
                                    "callType": { "type": "text" },
                                    "from": { "type": "text" },
                                    "gas": { "type": "text" },
                                    "input": { "type": "text" },
                                    "to": { "type": "text" },
                                    "value": { "type": "text" },
                                    "gasUsed": { "type": "text" },
                                    "output": { "type": "text" },
                                    "subtraces": { "type": "long" },
                                    "traceAddress": { "type": "long" },
                                    "type": { "type": "text" },
                                    "transactionHash": { "type": "text" },
                                    "depth": { "type": "text" },
                                    "extra": { "type": "text" }
                                }
                            },
                        }
                    }
                }
            },
            handler: async (delta) => {
                const data = delta.data;
                const blockHex = data.block.toString(16);
                const blockHash = createKeccakHash('keccak256').update(blockHex).digest('hex');
                delta['@evmReceipt'] = {
                    index: data.index,
                    hash: data.hash.toLowerCase(),
                    trx_index: data.trx_index,
                    block: data.block,
                    block_hash: blockHash,
                    trxid: data.trxid.toLowerCase(),
                    status: data.status,
                    epoch: data.epoch,
                    createdaddr: data.createdaddr.toLowerCase(),
                    gasused: parseInt('0x' + data.gasused),
                    ramused: parseInt('0x' + data.ramused),
                    output: data.output,
                    itxs: data.itxs || []
                };
                if (data.logs) {
                    delta['@evmReceipt']['logs'] = JSON.parse(data.logs);
                    if (delta['@evmReceipt']['logs'].length === 0) {
                        delete delta['@evmReceipt']['logs'];
                    }
                    else {
                        console.log('------- LOGS -----------');
                        console.log(delta['@evmReceipt']['logs']);
                        const bloom = new bloom_1.default();
                        for (const topic of delta['@evmReceipt']['logs'][0]['topics'])
                            bloom.add(Buffer.from(topic, 'hex'));
                        bloom.add(Buffer.from(delta['@evmReceipt']['logs'][0]['address'], 'hex'));
                        delta['@evmReceipt']['logsBloom'] = bloom.bitvector.toString('hex');
                    }
                }
                if (data.errors) {
                    delta['@evmReceipt']['errors'] = JSON.parse(data.errors);
                    if (delta['@evmReceipt']['errors'].length === 0) {
                        delete delta['@evmReceipt']['errors'];
                    }
                    else {
                        console.log('------- ERRORS -----------');
                        console.log(delta['@evmReceipt']['errors']);
                    }
                }
                delete delta.data;
            }
        });
    }
    loadActionHandlers() {
        // eosio.evm::raw
        this.actionHandlers.push({
            action: 'raw',
            contract: 'eosio.evm',
            mappings: {
                action: {
                    "@raw": {
                        "properties": {
                            "from": { "type": "keyword" },
                            "to": { "type": "keyword" },
                            "ram_payer": { "type": "keyword" },
                            "hash": { "type": "keyword" },
                            "value": { "type": "keyword" },
                            "value_d": { "type": "double" },
                            "nonce": { "type": "long" },
                            "gas_price": { "type": "double" },
                            "gas_limit": { "type": "double" },
                            "input_data": { "enabled": false }
                        }
                    }
                }
            },
            handler: (action) => {
                // attach action extras here
                const data = action['act']['data'];
                this.counter++;
                // decode internal EVM tx
                if (data.tx) {
                    try {
                        const tx = tx_1.Transaction.fromSerializedTx(Buffer.from(data.tx, 'hex'), {
                            common: this.common,
                        });
                        const txBody = {
                            hash: '0x' + tx.hash()?.toString('hex'),
                            to: tx.to?.toString(),
                            value: tx.value?.toString(),
                            nonce: tx.nonce?.toString(),
                            gas_price: tx.gasPrice?.toString(),
                            gas_limit: tx.gasLimit?.toString(),
                            input_data: '0x' + tx.data?.toString('hex'),
                        };
                        if (tx.isSigned()) {
                            txBody["from"] = tx.getSenderAddress().toString().toLowerCase();
                        }
                        else {
                            txBody["from"] = '0x' + data.sender.toLowerCase();
                        }
                        if (data.ram_payer) {
                            txBody["ram_payer"] = data.ram_payer;
                        }
                        if (txBody.value) {
                            // @ts-ignore
                            txBody['value_d'] = tx.value / this.decimalsBN;
                        }
                        action['@raw'] = txBody;
                        delete action['act']['data'];
                    }
                    catch (e) {
                        console.log(e);
                        console.log(data);
                    }
                }
            }
        });
    }
    addRoutes(server) {
        server.decorate('evm', new TelosEvmApi({
            endpoint: server["chain_api"],
            chainId: this.pluginConfig.chainId,
            ethPrivateKeys: [],
            fetch: node_fetch_1.default,
            telosContract: this.pluginConfig.contracts.main,
            telosPrivateKeys: [this.pluginConfig.signer_key]
        }));
        server.evm.setDebug(true);
        server.register(fastify_autoload_1.default, {
            dir: path_1.join(__dirname, 'routes'),
            options: this.pluginConfig
        });
    }
}
exports.default = TelosEvm;
//# sourceMappingURL=index.js.map