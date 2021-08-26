import {HyperionPlugin} from "../../hyperion-plugin";
import {FastifyInstance} from "fastify";
import fetch from "node-fetch";
import autoLoad from 'fastify-autoload';
import {join} from "path";
import {Transaction} from '@ethereumjs/tx';
import Common, {default as ethCommon} from '@ethereumjs/common';
import {HyperionDelta} from "../../../interfaces/hyperion-delta";
import {HyperionAction} from "../../../interfaces/hyperion-action";
import Bloom from "./bloom";

const BN = require('bn.js');
const createKeccakHash = require('keccak');
const {TelosEvmApi} = require('@telosnetwork/telosevm-js');

export interface TelosEvmConfig {
	signer_account: string;
	signer_permission: string;
	signer_key: string;
	contracts: {
		main: string;
	}
	chainId: number;
	debug : boolean;
}

export default class TelosEvm extends HyperionPlugin {

	hasApiRoutes = true;

	actionHandlers = [];
	deltaHandlers = [];
	common: Common;
	decimalsBN = new BN('1000000000000000000');
	baseChain = 'mainnet';
	hardfork = 'istanbul';
	counter = 0;
	pluginConfig: TelosEvmConfig;

	constructor(config: TelosEvmConfig) {
		super(config);
		if (this.baseConfig) {
			this.pluginConfig = this.baseConfig;
			if (config.contracts?.main) {
				this.dynamicContracts.push(config.contracts.main);
			}
			if (config.chainId) {
				this.common = ethCommon.forCustomChain(
					this.baseChain,
					{chainId: config.chainId},
					this.hardfork
				);
				this.loadActionHandlers();
				//this.loadDeltaHandlers();
			}
		}
	}

	loadDeltaHandlers() {
		/*
		// eosio.evm::receipt
		this.deltaHandlers.push({
			table: 'receipt',
			contract: 'eosio.evm',
			mappings: {
				delta: {
					"@evmReceipt": {
						"properties": {
							"index": {"type": "long"},
							"hash": {"type": "keyword"},
							"trx_index": {"type": "long"},
							"block": {"type": "long"},
							"block_hash": {"type": "keyword"},
							"trxid": {"type": "keyword"},
							"status": {"type": "byte"},
							"epoch": {"type": "long"},
							"createdaddr": {"type": "keyword"},
							"gasused": {"type": "long"},
							"ramused": {"type": "long"},
							"logs": {
								"properties": {
									"address": {"type": "keyword"},
									"data": {"enabled": false},
									"topics": {"type": "keyword"}
								}
							},
							"logsBloom": {"type": "keyword"},
							"output": {"enabled": false},
							"errors": {"enabled": false},
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
									"traceAddress": {"type": "long"},
                                    "type": { "type": "text" },
                                    "depth": { "type": "text" },
									"extra": {"type" : "text"}
                                }
                            },
						}
					}
				}
			},
			handler: async (delta: HyperionDelta) => {
				const data = delta.data;

				const blockHex = (data.block as number).toString(16);
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
					itxs: data.itxs	|| []
				};

				if (data.logs) {
					delta['@evmReceipt']['logs'] = JSON.parse(data.logs);
					if (delta['@evmReceipt']['logs'].length === 0) {
						delete delta['@evmReceipt']['logs'];
					} else {
						console.log('------- LOGS -----------');
						console.log(delta['@evmReceipt']['logs']);
						const bloom = new Bloom();
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
					} else {
						console.log('------- ERRORS -----------');
						console.log(delta['@evmReceipt']['errors'])
					}
				}

				delete delta.data;
			}
		});
		*/
	}

	loadActionHandlers() {

		// eosio.evm::receipt
		this.actionHandlers.push({
			action: 'receipt',
			// TODO: this contract account should come from the config?
			contract: 'eosio.evm',
			mappings: {
				action: {
					"@receipt": {
						"properties": {
							"trxid": {"type": "keyword"},
							"hash": {"type": "keyword"},
							"trx_index": {"type": "long"},
							"block": {"type": "long"},
							"block_hash": {"type": "keyword"},
							"from": {"type": "keyword"},
							"to": {"type": "keyword"},
							"input_data": {"enabled": false},
							"value": {"type": "keyword"},
							"value_d": {"type": "double"},
							"nonce": {"type": "long"},
							"v": {"type": "long"},
							"r": {"type": "long"},
							"s": {"type": "long"},
							"gas_price": {"type": "double"},
							"gas_limit": {"type": "double"},
							"status": {"type": "byte"},
							"epoch": {"type": "long"},
							"createdaddr": {"type": "keyword"},
							"gasused": {"type": "long"},
							"gasusedblock": {"type": "long"},
							"logs": {
								"properties": {
									"address": {"type": "keyword"},
									"data": {"enabled": false},
									"topics": {"type": "keyword"}
								}
							},
							"logsBloom": {"type": "keyword"},
							"output": {"enabled": false},
							"errors": {"enabled": false},
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
									"traceAddress": {"type": "long"},
									"type": { "type": "text" },
									"depth": { "type": "text" },
									"extra": {"type" : "text"}
								}
							},
						}
					}
				}
			},
			handler: (action: HyperionAction) => {
				// attach action extras here
				const data = action['act']['data'];
				this.counter++;

				// decode internal EVM tx
				if (data.tx) {
					const blockHex = (data.block as number).toString(16);
					const blockHash = createKeccakHash('keccak256').update(blockHex).digest('hex');
					try {
						const tx = Transaction.fromSerializedTx(Buffer.from(data.tx, 'hex'), {
							common: this.common,
						});
						const txBody = {
							trxid: 0,// TODO: action.trx_id.toLowerCase(),
							hash: '0x' + tx.hash()?.toString('hex'),
							trx_index: data.trx_index,
							block: data.block,
							block_hash: blockHash,
							to: tx.to?.toString(),
							input_data: '0x' + tx.data?.toString('hex'),
							value: tx.value?.toString(),
							nonce: tx.nonce?.toString(),
							gas_price: tx.gasPrice?.toString(),
							gas_limit: tx.gasLimit?.toString(),
							status: data.status,
							itxs: data.itxs	|| [],
							epoch: data.epoch,
							createdaddr: data.createdaddr.toLowerCase(),
							gasused: parseInt('0x' + data.gasused),
							gasusedblock: parseInt('0x' + data.gasusedblock),
							output: data.output,
						};

						if (tx.isSigned()) {
							txBody["from"] = tx.getSenderAddress().toString().toLowerCase();
							txBody["v"] = tx.v?.toString();
							txBody["r"] = tx.r?.toString();
							txBody["s"] = tx.s?.toString();
						} else {
							txBody["from"] = '0x' + data.sender.toLowerCase();
							//txBody["v"] = null;
							//txBody["r"] = null;
							//txBody["s"] = null;
						}

						if (data.logs) {
							txBody['logs'] = JSON.parse(data.logs);
							if (txBody['logs'].length === 0) {
								delete txBody['logs'];
							} else {
								console.log('------- LOGS -----------');
								console.log(txBody['logs']);
								const bloom = new Bloom();
								for (const topic of txBody['logs'][0]['topics'])
									bloom.add(Buffer.from(topic, 'hex'));
								bloom.add(Buffer.from(txBody['logs'][0]['address'], 'hex'));
								txBody['logsBloom'] = bloom.bitvector.toString('hex');
							}
						}

						if (data.errors) {
							txBody['errors'] = JSON.parse(data.errors);
							if (txBody['errors'].length === 0) {
								delete txBody['errors'];
							} else {
								console.log('------- ERRORS -----------');
								console.log(txBody['errors'])
							}
						}

						if (txBody.value) {
							// @ts-ignore
							txBody['value_d'] = tx.value / this.decimalsBN;
						}
						action['@receipt'] = txBody;
						delete action['act']['data'];
					} catch (e) {
						console.log(e);
						console.log(data);
					}
				}
			}
		});
	}

	addRoutes(server: FastifyInstance): void {
		server.decorate('evm', new TelosEvmApi({
			endpoint: server["chain_api"],
			chainId: this.pluginConfig.chainId,
			ethPrivateKeys: [],
			fetch: fetch,
			telosContract: this.pluginConfig.contracts.main,
			telosPrivateKeys: [this.pluginConfig.signer_key]
		}));
		server.evm.setDebug(true);
		server.register(autoLoad, {
			dir: join(__dirname, 'routes'),
			dirNameRoutePrefix: false,
			options: this.pluginConfig
		});
	}
}
