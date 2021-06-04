import { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { hLog } from "../../../../../helpers/common_functions";
import { TelosEvmConfig } from "../../index";

const BN = require('bn.js');
const abiDecoder = require("abi-decoder");
const abi = require("ethereumjs-abi");
const createKeccakHash = require('keccak')

const REVERT_FUNCTION_SELECTOR = '0x08c379a0'

function numToHex(input: number | string) {
	if (typeof input === 'number') {
		return '0x' + input.toString(16)
	} else {
		return '0x' + (parseInt(input, 10)).toString(16)
	}
}

function parseRevertReason(revertOutput) {
	if (!revertOutput || revertOutput.length < 138) {
		return '';
	}

	let reason = '';
	let trimmedOutput = revertOutput.substr(138);
	for (let i = 0; i < trimmedOutput.length; i += 2) {
		reason += String.fromCharCode(parseInt(trimmedOutput.substr(i, 2), 16));
	}
	return reason;
}

function jsonRcp2Error(reply: FastifyReply, type: string, requestId: string, message: string, code?: number) {
	let errorCode = code;
	switch (type) {
		case "InvalidRequest": {
			reply.statusCode = 400;
			errorCode = -32600;
			break;
		}
		case "MethodNotFound": {
			reply.statusCode = 404;
			errorCode = -32601;
			break;
		}
		case "ParseError": {
			reply.statusCode = 400;
			errorCode = -32700;
			break;
		}
		case "InvalidParams": {
			reply.statusCode = 400;
			errorCode = -32602;
			break;
		}
		case "InternalError": {
			reply.statusCode = 500;
			errorCode = -32603;
			break;
		}
		default: {
			reply.statusCode = 500;
			errorCode = -32603;
		}
	}
	let errorResponse = {
		jsonrpc: "2.0",
		id: requestId,
		error: {
			code: errorCode,
			message
		}
	};
}

interface EthLog {
	address: string;
	blockHash: string;
	blockNumber: string;
	data: string;
	logIndex: string;
	removed: boolean;
	topics: string[];
	transactionHash: string;
	transactionIndex: string;
}

interface TransactionError extends Error {
	errorMessage: string;
	data: any;
}

class TransactionError extends Error { }

export default async function (fastify: FastifyInstance, opts: TelosEvmConfig) {

	const methods: Map<string, (params?: any, headers?: any) => Promise<any> | any> = new Map();
	const decimalsBN = new BN('1000000000000000000');
	const zeros = "0x0000000000000000000000000000000000000000";
	const chainAddr = [
		"0xb1f8e55c7f64d203c1400b9d8555d050f94adf39",
		"0x9f510b19f1ad66f0dcf6e45559fab0d6752c1db7",
		"0xb8e671734ce5c8d7dfbbea5574fa4cf39f7a54a4",
		"0xb1d3fbb2f83aecd196f474c16ca5d9cffa0d0ffc",
	];
	const chainIds = [1, 3, 4, 42];
	const METAMASK_EXTENSION_ORIGIN = 'chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn';
	const ZERO_ADDR = '0x0000000000000000000000000000000000000000';
	const NULL_HASH = '0x0000000000000000000000000000000000000000000000000000000000000000';
	const GAS_OVER_ESTIMATE_MULTIPLIER = 1.25;

	// AUX FUNCTIONS

	function toChecksumAddress(address) {
		if (!address)
			return address

		address = address.toLowerCase().replace('0x', '')
		if (address.length != 40)
			address = address.padStart(40, "0");

		let hash = createKeccakHash('keccak256').update(address).digest('hex')
		let ret = '0x'

		for (var i = 0; i < address.length; i++) {
			if (parseInt(hash[i], 16) >= 8) {
				ret += address[i].toUpperCase()
			} else {
				ret += address[i]
			}
		}

		return ret
	}

	async function searchActionByHash(trxHash: string): Promise<any> {
		try {
			let _hash = trxHash.toLowerCase();
			if (_hash.startsWith("0x")) {
				_hash = _hash.slice(2);
			}
			const results = await fastify.elastic.search({
				index: `${fastify.manager.chain}-action-*`,
				body: {
					size: 1,
					query: {
						bool: {
							must: [{ term: { "@raw.hash": "0x" + _hash } }]
						}
					}
				}
			});
			return results?.body?.hits?.hits[0]?._source;
		} catch (e) {
			console.log(e);
			return null;
		}
	}

	async function searchDeltasByHash(trxHash: string): Promise<any> {
		try {
			let _hash = trxHash.toLowerCase();
			if (_hash.startsWith("0x")) {
				_hash = _hash.slice(2);
			}
			const results = await fastify.elastic.search({
				index: `${fastify.manager.chain}-delta-*`,
				body: {
					size: 1,
					query: {
						bool: {
							must: [{ term: { "@evmReceipt.hash": _hash } }]
						}
					}
				}
			});
			return results?.body?.hits?.hits[0]?._source;
		} catch (e) {
			console.log(e);
			return null;
		}
	}

	function buildLogsObject(logs: any[], blHash: string, blNumber: string, txHash: string, txIndex: string): EthLog[] {
		const _logs: EthLog[] = [];
		if (logs) {
			let counter = 0;
			for (const log of logs) {
				_logs.push({
					address: toChecksumAddress(log.address),
					blockHash: blHash,
					blockNumber: blNumber,
					data: log.data,
					logIndex: numToHex(counter),
					removed: false,
					topics: log.topics.map(t => '0x' + t),
					transactionHash: txHash,
					transactionIndex: txIndex
				});
				counter++;
			}
		}
		return _logs;
	}

	async function reconstructBlockFromReceipts(blockNumber: string, receipts: any[], full: boolean) {
		let actions = [];
		if (receipts.length > 0) {
			const rawResults = await fastify.elastic.search({
				index: `${fastify.manager.chain}-action-*`,
				body: {
					size: 1000,
					track_total_hits: true,
					query: {
						bool: {
							must: [
								{ term: { "act.account": "eosio.evm" } },
								{ term: { "act.name": "raw" } },
								{ term: { "block_num": receipts[0]._source.block_num } }
							]
						}
					}
				}
			});
			actions = rawResults?.body?.hits?.hits;
		}

		let blockHash;
		let blockHex: string;
		let timestamp: number;
		const trxs = [];
		for (const receiptDoc of receipts) {
			const receipt = receiptDoc._source['@evmReceipt'];
			if (!blockHash) {
				blockHash = '0x' + receipt['block_hash'];
			}
			if (!blockHex) {
				blockHex = '0x' + Number(receipt['block']).toString(16);
			}
			if (!timestamp) {
				timestamp = new Date(receiptDoc._source['@timestamp'] + 'Z').getTime();
			}
			if (!full) {
				trxs.push('0x' + receipt['hash']);
			} else {
				const txRawAction = actions.find(a => {
					return a._source['@raw']['hash'] === "0x" + receipt['hash']
				});
				if (txRawAction) {
					const rawAction = txRawAction._source['@raw']
					trxs.push({
						blockHash: blockHash,
						blockNumber: blockHex,
						from: toChecksumAddress(rawAction['from']),
						gas: receipt['gasused'],
						gasPrice: "0x" + Number(rawAction['gas_price']).toString(16),
						hash: "0x" + receipt['hash'],
						input: rawAction['input_data'],
						nonce: "0x" + Number(rawAction['nonce']).toString(16),
						to: toChecksumAddress(rawAction['to']),
						transactionIndex: "0x" + Number(receipt['trx_index']).toString(16),
						value: "0x0"
					});
				}
			}
		}
		// TODO: this better...

		if (!timestamp)
			timestamp = new Date().getTime()

		if (!blockHex)
			blockHex = '0x' + blockNumber;

		if (!blockHash)
			blockHash = blockHexToHash(blockHex);

		return {
			difficulty: "0x0",
			extraData: NULL_HASH,
			gasLimit: "0x989680",
			gasUsed: "0x989680",
			hash: blockHash,
			logsBloom: null,
			miner: ZERO_ADDR,
			mixHash: NULL_HASH,
			nonce: null,
			number: blockHex,
			parentHash: NULL_HASH,
			receiptsRoot: NULL_HASH,
			sha3Uncles: NULL_HASH,
			size: "0x0",
			stateRoot: NULL_HASH,
			timestamp: "0x" + timestamp?.toString(16),
			totalDifficulty: "0x0",
			transactions: trxs,
			transactionsRoot: NULL_HASH,
			uncles: []
		};
	}

	async function getDeltasByTerm(term: string, value: any) {
		const termStruct = {};
		termStruct[term] = value;
		const results = await fastify.elastic.search({
			index: `${fastify.manager.chain}-delta-*`,
			size: 1000,
			body: { query: { bool: { must: [{ term: termStruct }] } } }
		});
		return results?.body?.hits?.hits;
	}

	async function getCurrentBlockNumber() {
		const global = await fastify.eosjs.rpc.get_table_rows({
			code: "eosio",
			scope: "eosio",
			table: "global",
			json: true
		});
		const head_block_num = parseInt(global.rows[0].block_num, 10);
		return '0x' + head_block_num.toString(16);
	}

	function blockHexToHash(blockHex: string) {
		return `0x${createKeccakHash('keccak256').update(blockHex.replace(/^0x/, '')).digest('hex')}`;
	}

	async function toBlockNumber(blockParam: string) {
		console.log("toBlockNumber caleld with " + blockParam);
		if (blockParam == "latest" || blockParam == "pending")
			return await getCurrentBlockNumber();

		if (blockParam == "earliest")
			return "0x0";

		return blockParam;
	}

	// LOAD METHODS

	/**
	 * Returns the user-agent
	 */
	methods.set('web3_clientVersion', (params, headers) => {
		return headers['user-agent'];
	})

	/**
	 * Returns true if client is actively listening for network connections.
	 */
	methods.set('net_listening', () => true);

	/**
	 * Returns the current "latest" block number.
	 */
	methods.set('eth_blockNumber', async () => {
		try {
			return await getCurrentBlockNumber();
		} catch (e) {
			throw new Error('Request Failed: ' + e.message);
		}
	});

	/**
	 * Returns the current network id.
	 */
	methods.set('net_version', () => opts.chainId.toString());

	/**
	 * Returns the currently configured chain id, a value used in
	 * replay-protected transaction signing as introduced by EIP-155.
	 */
	methods.set('eth_chainId', () => "0x" + opts.chainId.toString(16));

	/**
	 * Returns a list of addresses owned by client.
	 */
	methods.set('eth_accounts', () => []);

	/**
	 * Returns the number of transactions sent from an address.
	 */
	methods.set('eth_getTransactionCount', async ([address]) => {
		return await fastify.evm.telos.getNonce(address.toLowerCase());
	});

	/**
	 * Returns the compiled smart contract code,
	 * if any, at a given address.
	 */
	methods.set('eth_getCode', async ([address]) => {
		try {
			const account = await fastify.evm.telos.getEthAccount(address.toLowerCase());
			if (account.code && account.code.length > 0) {
				return "0x" + Buffer.from(account.code).toString("hex");
			} else {
				return "0x0000";
			}
		} catch (e) {
			return "0x0000";
		}
	});

	/**
	 * Returns the value from a storage position at a given address.
	 */
	methods.set('eth_getStorageAt', async ([address, position]) => {
		return await fastify.evm.telos.getStorageAt(address.toLowerCase(), position);
	});

	/**
	 * Generates and returns an estimate of how much gas is necessary to
	 * allow the transaction to complete.
	 */
	methods.set('eth_estimateGas', async ([txParams, block]) => {
		if (txParams.value)
			txParams.value = txParams.value.replace(/^0x0x/, '0x');

		const encodedTx = await fastify.evm.createEthTx({
			...txParams,
			sender: txParams.from,
			gasPrice: 10000000000000000,
			gasLimit: 10000000000000000
		});

		const gas = await fastify.evm.telos.estimateGas({
			account: opts.signer_account,
			ram_payer: fastify.evm.telos.telosContract,
			tx: encodedTx,
			sender: txParams.from,
		});

		if (gas.startsWith(REVERT_FUNCTION_SELECTOR)) {
			let err = new TransactionError('Transaction reverted');
			err.errorMessage = `execution reverted: ${parseRevertReason(gas)}`;
			err.data = gas;
			throw err;
		}

		return `0x${Math.ceil((parseInt(gas, 16) * GAS_OVER_ESTIMATE_MULTIPLIER)).toString(16)}`;
	});

	/**
	 * Returns the current gas price in wei.
	 */
	methods.set('eth_gasPrice', async () => {
		let price = await fastify.evm.telos.getGasPrice();
		let priceInt = parseInt(price, 10);
		return isNaN(priceInt) ? null : "0x" + priceInt.toString(16);
	});

	/**
	 * Returns the balance of the account of given address.
	 */
	methods.set('eth_getBalance', async ([address]) => {
		try {
			const account = await fastify.evm.telos.getEthAccount(address.toLowerCase());
			const bal = account.balance as number;
			return "0x" + bal.toString(16);
		} catch (e) {
			return "0x0000";
		}
	});

	/**
	 * Returns the balance in native tokens (human readable format)
	 * of the account of given address.
	 */
	methods.set('eth_getBalanceHuman', async ([address]) => {
		try {
			const account = await fastify.evm.telos.getEthAccount(address.toLowerCase());
			const bal = account.balance as typeof BN;
			// @ts-ignore
			const balConverted = bal / decimalsBN;
			return balConverted.toString(10);
		} catch (e) {
			return "0";
		}
	});

	/**
	 * Executes a new message call immediately without creating a
	 * transaction on the block chain.
	 */
	methods.set('eth_call', async ([txParams]) => {
		if (chainIds.includes(opts.chainId) && chainAddr.includes(txParams.to)) {
			const { params: [users, tokens] } = abiDecoder.decodeMethod(txParams.data);
			if (tokens.value.length === 1 && tokens.value[0] === zeros) {
				const balances = await Promise.all(
					users.value.map((user) => {
						return methods.get('eth_getBalance')([user, null]);
					})
				);
				return "0x" + abi.rawEncode(balances.map(() => "uint256"), balances).toString("hex");
			}
		}
		let _value = new BN(0);
		if (txParams.value) {
			_value = new BN(Buffer.from(txParams.value.slice(2), "hex"));
		}
		const obj = {
			...txParams,
			value: _value,
			sender: txParams.from,
		};
		const encodedTx = await fastify.evm.createEthTx(obj);
		let output = await fastify.evm.telos.call({
			account: opts.signer_account,
			tx: encodedTx,
			sender: txParams.from,
		});
		if (output.startsWith(REVERT_FUNCTION_SELECTOR)) {
			let err = new TransactionError('Transaction reverted');
			err.errorMessage = `execution reverted: ${parseRevertReason(output)}`;
			err.data = output;
			throw err;
		}
		output = output.replace(/^0x/, '');
		return "0x" + output;
	});

	/**
	 * Submits a pre-signed transaction for broadcast to the
	 * Ethereum network.
	 */
	methods.set('eth_sendRawTransaction', async ([signedTx]) => {
		try {
			const rawData = await fastify.evm.telos.raw({
				account: opts.signer_account,
				tx: signedTx
			});
			const receiptResponse = await fastify.eosjs.rpc.get_table_rows({
				code: fastify.evm.telos.telosContract,
				scope: fastify.evm.telos.telosContract,
				table: 'receipt',
				key_type: 'sha256',
				index_position: 2,
				lower_bound: rawData.eth.transactionHash,
				upper_bound: rawData.eth.transactionHash,
				limit: 1
			});

			if (receiptResponse.rows.length && receiptResponse.rows[0].status === 0) {
				let receipt = receiptResponse.rows[0];
				let err = new TransactionError('Transaction error');
				let output = `0x${receipt.output}`
				if (output.startsWith(REVERT_FUNCTION_SELECTOR)) {
					err.errorMessage = `Error: VM Exception while processing transaction: revert ${parseRevertReason(output)}`;
				} else {
					let errors = JSON.parse(receipt.errors);
					err.errorMessage = errors[0];
				}
				err.data = {
					txHash: `0x${rawData.eth.transactionHash}`
				};
				throw err;
			}

			return '0x' + rawData.eth.transactionHash;
		} catch (e) {
			if (e instanceof TransactionError)
				throw e;

			console.log(e);
			return null;
		}
	});

	/**
	 * Submits transaction for broadcast to the Ethereum network.
	 */
	methods.set('eth_sendTransaction', async ([txParams]) => {
		const buf = Buffer.from(txParams.value.slice(2), "hex");
		const encodedTx = await fastify.evm.createEthTx({
			...txParams,
			value: new BN(buf),
			rawSign: true,
			sender: txParams.from,
		});
		try {
			const rawData = await fastify.evm.telos.raw({
				account: opts.signer_account,
				ram_payer: fastify.evm.telos.telosContract,
				tx: encodedTx
			});
			return "0x" + rawData.eth.transactionHash;
		} catch (e) {
			console.log(e);
			return null;
		}
	});

	/**
	 * Returns the receipt of a transaction by transaction hash.
	 */
	methods.set('eth_getTransactionReceipt', async ([trxHash]) => {
		if (trxHash) {

			// lookup receipt delta
			const receiptDelta = await searchDeltasByHash(trxHash);
			if (!receiptDelta) return null;
			const receipt = receiptDelta['@evmReceipt'];

			// lookup raw action
			const rawAction = await searchActionByHash(trxHash);
			if (!rawAction) return null;
			const raw = rawAction['@raw'];

			const _blockHash = '0x' + receipt['block_hash'];
			const _blockNum = numToHex(receipt['block']);
			const _gas = '0x' + (receipt['gasused'] as number).toString(16);
			let _contractAddr = null;
			if (receipt['createdaddr']) {
				_contractAddr = '0x' + receipt['createdaddr'];
			}

			return {
				blockHash: _blockHash,
				blockNumber: numToHex(receipt['block']),
				contractAddress: toChecksumAddress(_contractAddr),
				cumulativeGasUsed: _gas,
				from: toChecksumAddress(raw['from']),
				gasUsed: _gas,
				logsBloom: null,
				status: numToHex(receipt['status']),
				to: toChecksumAddress(raw['to']),
				transactionHash: raw['hash'],
				transactionIndex: numToHex(receipt['trx_index']),
				logs: buildLogsObject(
					receipt['logs'],
					_blockHash,
					_blockNum,
					raw['hash'],
					numToHex(receipt['trx_index'])
				),
				errors: receipt['errors'],
				output: '0x' + receipt['output']
			};
		} else {
			return null;
		}
	});

	/**
	 * Returns information about a transaction for a given hash.
	 */
	methods.set('eth_getTransactionByHash', async ([trxHash]) => {
		// lookup raw action
		const rawAction = await searchActionByHash(trxHash);
		if (!rawAction) return null;
		const raw = rawAction['@raw'];

		// lookup receipt delta
		const receiptDelta = await searchDeltasByHash(trxHash);
		if (!receiptDelta) return null;
		const receipt = receiptDelta['@evmReceipt'];

		const _blockHash = '0x' + receipt['block_hash'];
		const _blockNum = numToHex(receipt['block']);
		return {
			blockHash: _blockHash,
			blockNumber: _blockNum,
			from: toChecksumAddress(raw['from']),
			gas: numToHex(raw.gas_limit),
			gasPrice: numToHex(raw.gas_price),
			hash: raw['hash'],
			input: raw['input_data'],
			nonce: numToHex(raw['nonce']),
			// "r": "0x2a378831cf81d99a3f06a18ae1b6ca366817ab4d88a70053c41d7a8f0368e031",
			// "s": "0x450d831a05b6e418724436c05c155e0a1b7b921015d0fbc2f667aed709ac4fb5",
			to: toChecksumAddress(raw['to']),
			transactionIndex: numToHex(receipt['trx_index']),
			// "v": "0x25",
			value: numToHex(raw['value'])
		};
	});

	/**
	 * Returns information about a block by number.
	 */
	methods.set('eth_getBlockByNumber', async ([block, full]) => {
		const blockNumber = parseInt(await toBlockNumber(block), 16);
		const receipts = await getDeltasByTerm("@evmReceipt.block", blockNumber);
		return await reconstructBlockFromReceipts(blockNumber.toString(16), receipts, full);
	});

	/**
	 * Returns information about a block by hash.
	 */
	methods.set('eth_getBlockByHash', async ([hash, full]) => {
		let _hash = hash.toLowerCase();
		if (_hash.startsWith("0x")) {
			_hash = _hash.slice(2);
		}
		const receipts = await getDeltasByTerm("@evmReceipt.block_hash", _hash);
		return await reconstructBlockFromReceipts(_hash, receipts, full);
	});

	/**
	 * Returns the number of transactions in the block with
	 * the given block hash.
	 */
	methods.set('eth_getBlockTransactionCountByHash', async ([hash]) => {
		let _hash = hash.toLowerCase();
		if (_hash.startsWith("0x")) {
			_hash = _hash.slice(2);
		}
		const receipts = await getDeltasByTerm("@evmReceipt.block_hash", _hash);
		const txCount: number = receipts.length;
		return '0x' + txCount.toString(16);
	});

	/**
	 * Returns the number of transactions in the block with
	 * the given block number.
	 */
	methods.set('eth_getBlockTransactionCountByNumber', async ([block]) => {
		const blockNumber = parseInt(block, 16);
		const receipts = await getDeltasByTerm("@evmReceipt.block", blockNumber);
		const txCount: number = receipts.length;
		return '0x' + txCount.toString(16);
	});

	/**
	 * Returns the number of uncles in a block from a block
	 * matching the given block hash.
	 */
	methods.set('eth_getUncleCountByBlockHash', () => "0x0");

	/**
	 * Returns the number of uncles in a block from a block
	 * matching the given block number.
	 */
	methods.set('eth_getUncleCountByBlockNumber', () => "0x0");

	/**
	 * Returns an array of all logs matching a given filter object.
	 */
	methods.set('eth_getLogs', async (params) => {
		// query preparation
		let address: string = params.address;
		let topics: string[] = params.topics;
		let fromBlock: string | number = params.fromBlock;
		let toBlock: string | number = params.toBlock;
		let blockHash: string = params.blockHash;

		const queryBody: any = {
			bool: {
				must: [
					{ exists: { field: "@evmReceipt.logs" } }
				]
			}
		};

		if (blockHash) {
			if (fromBlock || toBlock) {
				throw new Error('fromBlock/toBlock are not allowed with blockHash query');
			}
			queryBody.bool.must.push({ term: { "@evmReceipt.block_hash": blockHash } })
		}

		if (fromBlock || toBlock) {
			const rangeObj = { range: { "@evmReceipt.block": {} } };
			if (fromBlock) {
				// console.log(`getLogs using fromBlock: ${fromBlock}`);
				rangeObj.range["@evmReceipt.block"]['gte'] = fromBlock;
			}
			if (toBlock) {
				// console.log(`getLogs using toBlock: ${toBlock}`);
				rangeObj.range["@evmReceipt.block"]['lte'] = toBlock;
			}
			queryBody.bool.must.push(rangeObj);
		}

		if (address) {
			address = address.toLowerCase();
			if (address.startsWith('0x')) {
				address = address.slice(2);
			}
			// console.log(`getLogs using address: ${address}`);
			queryBody.bool.must.push({ term: { "@evmReceipt.logs.address": address } })
		}

		if (topics && topics.length > 0) {
			// console.log(`getLogs using topics:\n${topics}`);
			queryBody.bool.must.push({
				terms: {
					"@evmReceipt.logs.topics": topics.map(topic => {
						return topic.startsWith('0x') ? topic.slice(2).toLowerCase() : topic.toLowerCase();
					})
				}
			})
		}

		// search
		try {
			const searchResults = await fastify.elastic.search({
				index: `${fastify.manager.chain}-delta-*`,
				size: 1000,
				body: {
					query: queryBody,
					sort: [{ "@evmReceipt.trx_index": { order: "asc" } }]
				}
			});

			// processing
			const results = [];
			let logCount = 0;
			for (const hit of searchResults.body.hits.hits) {
				const doc = hit._source;
				if (doc['@evmReceipt'] && doc['@evmReceipt']['logs']) {
					for (const log of doc['@evmReceipt']['logs']) {
						results.push({
							address: '0x' + log.address,
							blockHash: '0x' + doc['@evmReceipt']['block_hash'],
							blockNumber: numToHex(doc['@evmReceipt']['block']),
							data: '0x' + log.data,
							logIndex: numToHex(logCount),
							removed: false,
							topics: log.topics.map(t => '0x' + t),
							transactionHash: doc['@evmReceipt']['hash'],
							transactionIndex: numToHex(doc['@evmReceipt']['trx_index'])
						});
						logCount++;
					}
				}
			}

			return results;
		} catch (e) {
			console.log(JSON.stringify(e, null, 2));
			return [];
		}
	});

	// END METHODS

	/**
	 * Main JSON RPC 2.0 Endpoint
	 */
	fastify.post('/', async (request: FastifyRequest, reply: FastifyReply) => {
		const { jsonrpc, id, method, params } = request.body as any;
		if (jsonrpc !== "2.0") {
			return jsonRcp2Error(reply, "InvalidRequest", id, "Invalid JSON RPC");
		}
		if (methods.has(method)) {
			const tRef = process.hrtime.bigint();
			const func = methods.get(method);
			try {
				const result = await func(params, request.headers);
				let origin;
				if (request.headers['origin'] === METAMASK_EXTENSION_ORIGIN) {
					origin = 'MetaMask';
				} else {
					if (request.headers['origin']) {
						origin = request.headers['origin'];
					} else {
						origin = request.headers['user-agent'];
					}
				}
				const _usage = reply.getHeader('x-ratelimit-remaining');
				const _limit = reply.getHeader('x-ratelimit-limit');
				const _ip = request.headers['x-real-ip'];

				const duration = ((Number(process.hrtime.bigint()) - Number(tRef)) / 1000).toFixed(3);
				hLog(`${new Date().toISOString()} - ${duration} μs - ${_ip} (${_usage}/${_limit}) - ${origin} - ${method}`);
				console.log(`REQ: ${JSON.stringify(params)} | RESP: ${typeof result == 'object' ? JSON.stringify(result, null, 2) : result}`);
				reply.send({ id, jsonrpc, result });
			} catch (e) {
				if (e instanceof TransactionError) {
					hLog(`VM execution error, reverted: ${e.errorMessage}`, method, JSON.stringify(params, null, 2));
					let code = 3;
					let message = e.errorMessage;
					let data = e.data;
					let error = { code, message, data };
					reply.send({ id, jsonrpc, error });
					console.log(`REQ: ${JSON.stringify(params)} | ERROR RESP: ${JSON.stringify(error, null, 2)}`);
					return;
				}
				hLog(e.message, method, JSON.stringify(params, null, 2));
				console.log(JSON.stringify(e, null, 2));
				return jsonRcp2Error(reply, "InternalError", id, e.message);
			}
		} else {
			return jsonRcp2Error(reply, 'MethodNotFound', id, `Invalid method: ${method}`);
		}
	});
}
export const autoPrefix = '/evm';
