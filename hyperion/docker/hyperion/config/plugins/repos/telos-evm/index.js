"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
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
const BN = require('bn.js');
const createKeccakHash = require('keccak');
const { TelosEvmApi } = require('@telosnetwork/telosevm-js');
class TelosEvm extends hyperion_plugin_1.HyperionPlugin {
    constructor(config) {
        var _a;
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
            if ((_a = config.contracts) === null || _a === void 0 ? void 0 : _a.main) {
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
                            "output": { "enabled": false },
                            "errors": { "enabled": false },
                        }
                    }
                }
            },
            handler: (delta) => __awaiter(this, void 0, void 0, function* () {
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
                    output: data.output
                };
                if (data.logs) {
                    delta['@evmReceipt']['logs'] = JSON.parse(data.logs);
                    if (delta['@evmReceipt']['logs'].length === 0) {
                        delete delta['@evmReceipt']['logs'];
                    }
                    else {
                        console.log('------- LOGS -----------');
                        console.log(delta['@evmReceipt']['logs']);
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
            })
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
                var _a, _b, _c, _d, _e, _f, _g;
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
                            hash: '0x' + ((_a = tx.hash()) === null || _a === void 0 ? void 0 : _a.toString('hex')),
                            to: (_b = tx.to) === null || _b === void 0 ? void 0 : _b.toString(),
                            value: (_c = tx.value) === null || _c === void 0 ? void 0 : _c.toString(),
                            nonce: (_d = tx.nonce) === null || _d === void 0 ? void 0 : _d.toString(),
                            gas_price: (_e = tx.gasPrice) === null || _e === void 0 ? void 0 : _e.toString(),
                            gas_limit: (_f = tx.gasLimit) === null || _f === void 0 ? void 0 : _f.toString(),
                            input_data: '0x' + ((_g = tx.data) === null || _g === void 0 ? void 0 : _g.toString('hex')),
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
        server.register(fastify_autoload_1.default, {
            dir: path_1.join(__dirname, 'routes'),
            options: this.pluginConfig
        });
    }
}
exports.default = TelosEvm;
//# sourceMappingURL=index.js.map