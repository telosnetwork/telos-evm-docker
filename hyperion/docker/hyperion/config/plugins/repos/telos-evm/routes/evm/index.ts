import { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { TelosEvmConfig } from "../../index";
import Bloom from "../../bloom";
import DebugLogger from "../../debugLogging";

const BN = require('bn.js');
const abiDecoder = require("abi-decoder");
const abi = require("ethereumjs-abi");
const createKeccakHash = require('keccak')
const GAS_PRICE_OVERESTIMATE = 1.25

const RECEIPT_LOG_START = "RCPT{{";
const RECEIPT_LOG_END = "}}RCPT";

const REVERT_FUNCTION_SELECTOR = '0x08c379a0'
const REVERT_PANIC_SELECTOR = '0x4e487b71'

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

function parsePanicReason(revertOutput) {
	let trimmedOutput = revertOutput.slice(-2)
	let reason;

	switch(trimmedOutput) {
		case "01":
			reason = "If you call assert with an argument that evaluates to false.";
		  break;
		case "11":
			reason = "If an arithmetic operation results in underflow or overflow outside of an unchecked { ... } block.";
		  break;
		case "12":
			reason = "If you divide or modulo by zero (e.g. 5 / 0 or 23 % 0).";
		  break;
		case "21":
			reason = "If you convert a value that is too big or negative into an enum type.";
			break;
		case "31":
			reason = "If you call .pop() on an empty array.";
			break;
		case "32":
			reason = "If you access an array, bytesN or an array slice at an out-of-bounds or negative index (i.e. x[i] where i >= x.length or i < 0).";
			break;
		case "41":
			reason = "If you allocate too much memory or create an array that is too large.";
			break;	
		case "51":
			reason = "If you call a zero-initialized variable of internal function type.";
			break;		
		default:
			reason = "Default panic message";
	}	
	return reason;
}

function toOpname(opcode) {
	switch (opcode) {
		case "f0":
			return "create";
		case "f1":
			return "call";
		case "f4":
			return "delegatecall";
		case "f5":
			return "create2";
		case "fa":
			return "staticcall";
		case "ff":
			return "selfdestruct";
		default:
			return "unkown";
	}
}

function jsonRPC2Error(reply: FastifyReply, type: string, requestId: string, message: string, code?: number) {
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
	code: number;
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
	let Logger = new DebugLogger(opts.debug);
	

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
		Logger.log(`searching action by hash: ${trxHash}`)
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
			//Logger.log(`searching action by hash: ${trxHash} got result: \n${JSON.stringify(results?.body)}`)
			return results?.body?.hits?.hits[0]?._source;
		} catch (e) {
			console.log(e);
			return null;
		}
	}

	/*
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
							must: [{ term: { "@receipt.hash": _hash } }]
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
	*/

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
		let blockHash;
		let blockHex: string;
		let gasLimit = 0;
		let gasUsedBlock = 0;
		let timestamp: number;
		let logsBloom: any = null;
		let bloom = new Bloom();
		const trxs = [];
		//Logger.log(`Reconstructing block from receipts: ${JSON.stringify(receipts)}`)	
		for (const receiptDoc of receipts) {
			const receipt = receiptDoc._source['@raw'];

			gasLimit += receipt["gas_limit"];

			let trxGasUsedBlock = receipt["gasusedblock"];
			if (trxGasUsedBlock > gasUsedBlock) {
				gasUsedBlock = trxGasUsedBlock;
			}
			if (!blockHash) {
				blockHash = '0x' + receipt['block_hash'];
			}
			if (!blockHex) {
				blockHex = '0x' + Number(receipt['block']).toString(16);
			}
			if (!timestamp) {
				timestamp = new Date(receiptDoc._source['@timestamp'] + 'Z').getTime() / 1000 | 0;
			}
			if (receipt['logsBloom']){
				bloom.or(new Bloom(Buffer.from(receipt['logsBloom'], "hex")));
				logsBloom = "0x" + bloom.bitvector.toString("hex");
			}
			if (!full) {
				trxs.push(receipt['hash']);
			} else {
				trxs.push({
					blockHash: blockHash,
					blockNumber: blockHex,
					from: toChecksumAddress(receipt['from']),
					gas: receipt['gasused'],
					gasPrice: "0x" + Number(receipt['gas_price']).toString(16),
					hash: receipt['hash'],
					input: receipt['input_data'],
					nonce: "0x" + Number(receipt['nonce']).toString(16),
					to: toChecksumAddress(receipt['to']),
					transactionIndex: "0x" + Number(receipt['trx_index']).toString(16),
					value: "0x" + Number(receipt['value']).toString(16)
				});
			}
		}
		// TODO: this better, receipt.epoch is what we want, but if we got this far we don't have any transactions to pull from

		if (!timestamp)
			timestamp = new Date().getTime() / 1000 | 0

		if (!blockHex)
			blockHex = '0x' + blockNumber;

		if (!blockHash)
			blockHash = blockHexToHash(blockHex);

		return {
			difficulty: "0x0",
			extraData: NULL_HASH,
			gasLimit: numToHex(gasLimit),
			gasUsed: gasUsedBlock,
			hash: blockHash,
			logsBloom: logsBloom,
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

	async function getReceiptsByTerm(term: string, value: any) {
		const termStruct = {};
		termStruct[term] = value;
		const results = await fastify.elastic.search({
			index: `${fastify.manager.chain}-action-*`,
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
		if (blockParam == "latest" || blockParam == "pending")
			return await getCurrentBlockNumber();

		if (blockParam == "earliest")
			return "0x0";

		return blockParam;
	}

	async function hasTopics(topics: string[], topicsFilter: string[]) {
		const topicsFiltered = [];
		
		for (const [index,topic] of topicsFilter.entries()) {
			if (topic === null) {
				topicsFiltered.push(true);
			} else if (topic.includes(topics[index])) {
				topicsFiltered.push(true);
			} else if (topics[index] === topic) {
				topicsFiltered.push(true);
			} else {
				topicsFiltered.push(false);
			}
		}
		return topicsFiltered.every(t => t === true);
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
				return "0x0";
			}
		} catch (e) {
			return "0x0";
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
		if (txParams.hasOwnProperty('value')) {
			const intValue = parseInt(txParams.value, 16);
			txParams.value = isNaN(intValue) ? 0 : intValue;
		}

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
		if (gas.startsWith(REVERT_PANIC_SELECTOR)) {
			let err = new TransactionError('Transaction reverted');
			err.errorMessage = `execution reverted: ${parsePanicReason(gas)}`;
			err.data = gas;
			throw err;
		}

		/*  from contract:
			if (estimate_gas) {
				if (result.er != ExitReason::returned) {
					eosio::print("0x" + bin2hex(result.output));
				} else {
					eosio::print("0x" + intx::hex(gas_used));
				}
				eosio::check(false, "");
			}

			if gas == '0x', the transaction reverted without any output
		*/
		if (gas == '0x') {
			let err = new TransactionError('Transaction reverted');
			err.errorMessage = `execution reverted: no output`;
			err.data = gas;
			throw err;
		}

		let toReturn = `0x${Math.ceil((parseInt(gas, 16) * GAS_OVER_ESTIMATE_MULTIPLIER)).toString(16)}`;
		Logger.log(`From contract, gas estimate is ${gas}, with multiplier returning ${toReturn}`)
		//let toReturn = `0x${Math.ceil((parseInt(gas, 16) * GAS_OVER_ESTIMATE_MULTIPLIER)).toString(16)}`;
		return toReturn;
	});

	/**
	 * Returns the current gas price in wei.
	 */
	methods.set('eth_gasPrice', async () => {
		let price = await fastify.evm.telos.getGasPrice();
		let priceInt = parseInt(price, 16) * GAS_PRICE_OVERESTIMATE;
		return isNaN(priceInt) ? null : "0x" + Math.floor(priceInt).toString(16);
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
		try {
			let output = await fastify.evm.telos.call({
				account: opts.signer_account,
				tx: encodedTx,
				sender: txParams.from,
			});
			output = output.replace(/^0x/, '');
			return "0x" + output;
		} catch (e) {
			if (e.evmCallOutput) {
				let output = "0x" + (e.evmCallOutput.replace(/^0x/, ''));
				let err = new TransactionError('Transaction reverted');
				err.data = output;

				if (output.startsWith(REVERT_FUNCTION_SELECTOR)) {
					err.errorMessage = `execution reverted: ${parseRevertReason(output)}`;
				} else if (output.startsWith(REVERT_PANIC_SELECTOR)) {
					err.errorMessage = `execution reverted: ${parsePanicReason(output)}`;
				} else {
					err.errorMessage = 'Error: Transaction reverted without a reason string';
				}

				throw err;
			}

			throw e;
		}
	});

	/**
	 * Submits a pre-signed transaction for broadcast to the
	 * Ethereum network.
	 */
	methods.set('eth_sendRawTransaction', async ([signedTx]) => {
		try {
			const rawResponse = await fastify.evm.telos.raw({
				account: opts.signer_account,
				tx: signedTx,
				ram_payer: fastify.evm.telos.telosContract,
			});

			let consoleOutput = rawResponse.telos.processed.action_traces[0].console;

			let receiptLog = consoleOutput.slice(consoleOutput.indexOf(RECEIPT_LOG_START) + RECEIPT_LOG_START.length, consoleOutput.indexOf(RECEIPT_LOG_END));
			let receipt = JSON.parse(receiptLog);

			if (receipt.status === 0) {
				let err = new TransactionError('Transaction error');
				let output = `0x${receipt.output}`
				if (output.startsWith(REVERT_FUNCTION_SELECTOR)) {
					err.errorMessage = `Error: VM Exception while processing transaction: reverted with reason string '${parseRevertReason(output)}'`;
				} else if (output.startsWith(REVERT_PANIC_SELECTOR)) {
					err.errorMessage = `Error: VM Exception while processing transaction: reverted with reason string '${parsePanicReason(output)}'`;
				}				
				else {
					// TODO: improve errors in the contract and then use them here... 
					//   hardhat tests fail because our message from the contract is "One of the actions in this transaction was REVERTed."
					//   and hardhat is looking for the string `revert` (lower case) when it's doing "expectRevert.unspecified()"
					//let errors = receipt.errors;
					// Borrowed message from hardhat node
					if (receipt.errors.length > 0 && receipt.errors[0].toLowerCase().indexOf('revert') !== -1)
						err.errorMessage = `Transaction reverted: function selector was not recognized.`;
					else
						err.errorMessage = `Error: VM Exception while processing transaction: ${receipt.errors[0]}`;
				}

				err.data = {
					txHash: `0x${rawResponse.eth.transactionHash}`
				};
				throw err;
			}

			return '0x' + rawResponse.eth.transactionHash;
		} catch (e) {
			// TODO: here we probably should not just return null, that causes tests to hang
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
			//const receiptDelta = await searchDeltasByHash(trxHash);
			//if (!receiptDelta) return null;
			//const receipt = receiptDelta['@receipt'];

			// lookup receipt action
			const receiptAction = await searchActionByHash(trxHash);
			if (!receiptAction) return null;
			const receipt = receiptAction['@raw'];

			//Logger.log(`get transaction receipt got ${JSON.stringify(receipt)}`)
			const _blockHash = '0x' + receipt['block_hash'];
			const _blockNum = numToHex(receipt['block']);
			const _gas = '0x' + (receipt['gasused'] as number).toString(16);
			let _contractAddr = null;
			if (receipt['createdaddr']) {
				_contractAddr = '0x' + receipt['createdaddr'];
			}
			let _logsBloom = null;
			if (receipt['logsBloom']) {
				_logsBloom = '0x' + receipt['logsBloom'];
			}

			return {
				blockHash: _blockHash,
				blockNumber: numToHex(receipt['block']),
				contractAddress: toChecksumAddress(_contractAddr),
				cumulativeGasUsed: _gas,
				from: toChecksumAddress(receipt['from']),
				gasUsed: _gas,
				logsBloom: _logsBloom,
				status: numToHex(receipt['status']),
				to: toChecksumAddress(receipt['to']),
				transactionHash: receipt['hash'],
				transactionIndex: numToHex(receipt['trx_index']),
				logs: buildLogsObject(
					receipt['logs'],
					_blockHash,
					_blockNum,
					receipt['hash'],
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
		const receiptAction = await searchActionByHash(trxHash);
		if (!receiptAction) return null;
		const receipt = receiptAction['@raw'];

		// lookup receipt delta
		//const receiptDelta = await searchDeltasByHash(trxHash);
		//if (!receiptDelta) return null;
		//const receipt = receiptDelta['@receipt'];

		const _blockHash = '0x' + receipt['block_hash'];
		const _blockNum = numToHex(receipt['block']);
		return {
			blockHash: _blockHash,
			blockNumber: _blockNum,
			from: toChecksumAddress(receipt['from']),
			gas: numToHex(receipt.gas_limit),
			gasPrice: numToHex(receipt.gas_price),
			hash: receipt['hash'],
			input: receipt['input_data'],
			nonce: numToHex(receipt['nonce']),
			to: toChecksumAddress(receipt['to']),
			transactionIndex: numToHex(receipt['trx_index']),
			value: numToHex(receipt['value']),
			v: '0x' + receipt['v'],
			r: '0x' + receipt['r'],
			s: '0x' + receipt['s'],
		};
	});

	/**
	 * Returns information about a block by number.
	 */
	methods.set('eth_getBlockByNumber', async ([block, full]) => {
		const blockNumber = parseInt(await toBlockNumber(block), 16);
		const receipts = await getReceiptsByTerm("@raw.block", blockNumber);
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
		const receipts = await getReceiptsByTerm("@raw.block_hash", _hash);
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
		const receipts = await getReceiptsByTerm("@raw.block_hash", _hash);
		const txCount: number = receipts.length;
		return '0x' + txCount.toString(16);
	});

	/**
	 * Returns the number of transactions in the block with
	 * the given block number.
	 */
	methods.set('eth_getBlockTransactionCountByNumber', async ([block]) => {
		const blockNumber = parseInt(block, 16);
		const receipts = await getReceiptsByTerm("@raw.block", blockNumber);
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
	methods.set('eth_getLogs', async ([parameters]) => {
		// console.log(parameters);
		let params = await parameters; // Since we are using async/await, the parameters are actually a Promise
		
		// query preparation
		let address: string = params.address;
		let topics: string[] = params.topics;
		let fromBlock: string | number = parseInt(await toBlockNumber(params.fromBlock), 16);
		let toBlock: string | number = parseInt(await toBlockNumber(params.toBlock), 16);
		let blockHash: string = params.blockHash;

		const queryBody: any = {
			bool: {
				must: [
					{ exists: { field: "@raw.logs" } }
				]
			}
		};

		if (blockHash) {
			if (fromBlock || toBlock) {
				throw new Error('fromBlock/toBlock are not allowed with blockHash query');
			}
			queryBody.bool.must.push({ term: { "@raw.block_hash": blockHash } })
		}

		if (fromBlock || toBlock) {
			const rangeObj = { range: { "@raw.block": {} } };
			if (fromBlock) {
				// console.log(`getLogs using fromBlock: ${fromBlock}`);
				rangeObj.range["@raw.block"]['gte'] = fromBlock;
			}
			if (toBlock) {
				// console.log(`getLogs using toBlock: ${toBlock}`);
				rangeObj.range["@raw.block"]['lte'] = toBlock;
			}
			queryBody.bool.must.push(rangeObj);
		}

		if (address) {
			address = address.toLowerCase();
			if (address.startsWith('0x')) {
				address = address.slice(2);
			}
			// console.log(`getLogs using address: ${address}`);
			queryBody.bool.must.push({ term: { "@raw.logs.address": address } })
		}

		if (topics && topics.length > 0) {
			// console.log(`getLogs using topics:\n${topics}`);
			topics = topics.map(topic => {
				return topic.startsWith('0x') ? topic.slice(2).toLowerCase() : topic.toLowerCase();
			})
			queryBody.bool.must.push({
				terms: {
					"@raw.logs.topics": topics
				}
			})
		}

		// search
		try {
			// Logger.log(`About to run logs query with queryBody: ${JSON.stringify(queryBody)}`)
			const searchResults = await fastify.elastic.search({
				index: `${fastify.manager.chain}-action-*`,
				size: 1000,
				body: {
					query: queryBody,
					sort: [{ "@raw.trx_index": { order: "asc" } }]
				}
			});

			// Logger.log(`Logs query result: ${JSON.stringify(searchResults)}`)
			// processing
			const results = [];
			let logCount = 0;
			for (const hit of searchResults.body.hits.hits) {
				const doc = hit._source;
				if (doc['@raw'] && doc['@raw']['logs']) {
					for (const log of doc['@raw']['logs']) {
						if (
							doc['@raw']["block"] >= fromBlock &&
							doc['@raw']["block"] <= toBlock &&
							log.address.toLowerCase() === address.toLowerCase() &&
							await hasTopics(log.topics, topics)
							|| blockHash === doc['@raw']['block_hash'] &&
							log.address.toLowerCase() === address.toLowerCase() &&
							await hasTopics(log.topics, topics)
							) 
						{
							results.push({
								address: '0x' + log.address,
								blockHash: '0x' + doc['@raw']['block_hash'],
								blockNumber: numToHex(doc['@raw']['block']),
								data: '0x' + log.data,
								logIndex: numToHex(logCount),
								removed: false,
								topics: log.topics.map(t => '0x' + t),
								transactionHash: doc['@raw']['hash'],
								transactionIndex: numToHex(doc['@raw']['trx_index'])
							});
						}
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

	/**
	 * Returns the internal transaction trace filter matching the given filter object.
	 * https://openethereum.github.io/JSONRPC-trace-module#trace_filter
	 * curl --data '{"method":"trace_filter","params":[{"fromBlock":"0x2ed0c4","toBlock":"0x2ed128","toAddress":["0x8bbB73BCB5d553B5A556358d27625323Fd781D37"],"after":1000,"count":100}],"id":1,"jsonrpc":"2.0"}' -H "Content-Type: application/json" -X POST localhost:7000/evm
	 * 
	 * Check the eth_getlogs function above for help
	 */
	methods.set('trace_filter', async ([parameters]) => {
		let params = await parameters;
		// query preparation
		const results = [];
		for (const param_obj of params) {
			// console.log(param_obj);
			let fromAddress = param_obj.fromAddress;
			let toAddress = param_obj.toAddress;
			let fromBlock: string | number = parseInt(await toBlockNumber(param_obj.fromBlock), 16);
			let toBlock: string | number = parseInt(await toBlockNumber(param_obj.toBlock), 16);
			let after:  number = param_obj.after; //TODO what is this?
			let count: number = param_obj.count;

			if (typeof fromAddress !== 'undefined') {
				fromAddress.forEach((addr, index) => fromAddress[index] = toChecksumAddress(addr).slice(2).replace(/^0+/, '').toLowerCase());
			}
			if (typeof toAddress !== 'undefined') {
				toAddress.forEach((addr, index) => toAddress[index] = toChecksumAddress(addr).slice(2).replace(/^0+/, '').toLowerCase());
			}

			const queryBody: any = {
				bool: {
					must: [
						{ exists: { field: "@raw.itxs" } }
					]
				}
			};

			if (fromBlock || toBlock) {
				const rangeObj = { range: { "@raw.block": {} } };
				if (fromBlock) {
					// console.log(`getLogs using toBlock: ${toBlock}`);
					rangeObj.range["@raw.block"]['gte'] = fromBlock;
				}
				if (toBlock) {
					// console.log(`getLogs using fromBlock: ${params.fromBlock}`);
					rangeObj.range["@raw.block"]['lte'] = toBlock;
				}
				queryBody.bool.must.push(rangeObj);
			}
			
			if (fromAddress) {
				// console.log(fromAddress);
				const matchFrom = { terms: { "@raw.itxs.from": {} } };
				matchFrom.terms["@raw.itxs.from"] = fromAddress;
				queryBody.bool.must.push(matchFrom);
			}
			if (toAddress) {
				// console.log(toAddress);
				const matchTo = { terms: { "@raw.itxs.to": {} } };
				matchTo.terms["@raw.itxs.to"] = toAddress;
				queryBody.bool.must.push(matchTo);
			}

			// search
			try {
				const searchResults = await fastify.elastic.search({
					index: `${fastify.manager.chain}-action-*`,
					size: count,
					body: {
						query: queryBody,
						sort: [{ "@raw.trx_index": { order: "asc" } }]
					}
				});

				// processing
				let logCount = 0;
				for (const hit of searchResults.body.hits.hits) {
					const doc = hit._source;
					if (doc['@raw'] && doc['@raw']['itxs']) {
						for (const itx of doc['@raw']['itxs']) {
							results.push({
								action: {
									callType: toOpname(itx.callType),
									//why is 0x not in the receipt table?
									from: toChecksumAddress(itx.from),
									gas: '0x' + itx.gas,
									input: '0x' + itx.input,
									to: toChecksumAddress(itx.to),
									value: '0x' + itx.value
								},
								blockHash: '0x' + doc['@raw']['block_hash'],
								blockNumber: doc['@raw']['block'],
								result: {
									gasUsed: '0x' + itx.gasUsed,
									output: '0x' + itx.output,
								},
								subtraces: itx.subtraces,
								traceAddress: itx.traceAddress,
								transactionHash: '0x' + doc['@raw']['hash'],
								transactionPosition: doc['@raw']['trx_index'],
								type: itx.type});
							logCount++;
						}
					}
				}
			} catch (e) {
				console.log(JSON.stringify(e, null, 2));
				return [];
			}
		}	
		return results;
	});

	/**
	 * Returns the internal transaction trace filter matching the given filter object.
	 * https://openethereum.github.io/JSONRPC-trace-module#trace_transaction
	 * curl --data '{"method":"trace_transaction","params":["0x17104ac9d3312d8c136b7f44d4b8b47852618065ebfa534bd2d3b5ef218ca1f3"],"id":1,"jsonrpc":"2.0"}' -H "Content-Type: application/json" -X POST localhost:7000/evm
	 */
	 methods.set('trace_transaction', async ([trxHash]) => {
		// query preparation
		if (trxHash) {

			// lookup receipt delta
			//const receiptDelta = await searchDeltasByHash(trxHash);
			//if (!receiptDelta) return null;
			const receiptAction = await searchActionByHash(trxHash);
			if (!receiptAction) return null;
			const receipt = receiptAction['@raw'];

			// processing
			const results = [];
			let logCount = 0;
			if (receipt && receipt['itxs']) {
				for (const itx of receipt['itxs']) {
					results.push({
						action: {
							callType: toOpname(itx.callType),
							//why is 0x not in the receipt table?
							from: toChecksumAddress(itx.from),
							gas: '0x' + itx.gas,
							input: '0x' + itx.input,
							to: toChecksumAddress(itx.to),
							value: '0x' + itx.value
						},
						blockHash: '0x' + receipt['block_hash'],
						blockNumber: receipt['block'],
						result: {
							gasUsed: '0x' + itx.gasUsed,
							output: '0x' + itx.output,
						},
						subtraces: itx.subtraces,
						traceAddress: itx.traceAddress,
						transactionHash: receipt['hash'],
						transactionPosition: receipt['trx_index'],
						type: itx.type});
					logCount++;
				}
			}
				return results;
			} else {
				return null;
			}

	});

	// END METHODS

	/**
	 * Main JSON RPC 2.0 Endpoint
	 */

	 const schema: any = {
		summary: 'EVM JSON-RPC 2.0',
		tags: ['evm'],
	};

	fastify.post('/evm', { schema }, async (request: FastifyRequest, reply: FastifyReply) => {
		const { jsonrpc, id, method, params } = request.body as any;
		if (jsonrpc !== "2.0") {
			return jsonRPC2Error(reply, "InvalidRequest", id, "Invalid JSON RPC");
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
				
				Logger.log(`${new Date().toISOString()} - ${duration} μs - ${_ip} (${_usage}/${_limit}) - ${origin} - ${method}`);
				Logger.log(`REQ: ${JSON.stringify(params)} | RESP: ${typeof result == 'object' ? JSON.stringify(result, null, 2) : result}`);
				reply.send({ id, jsonrpc, result });
			} catch (e) {
				if (e instanceof TransactionError) {
					Logger.log(`VM execution error, reverted: ${e.errorMessage} | Method: ${method} | RESP: ${JSON.stringify(params, null, 2)}`);
					let code = e.code || 3;
					let message = e.errorMessage;
					let data = e.data;
					let error = { code, message, data };
					reply.send({ id, jsonrpc, error });
					Logger.log(`REQ: ${JSON.stringify(params)} | ERROR RESP: ${JSON.stringify(error, null, 2)}`);
					return;
				}
				
				Logger.log(`ErrorMessage: ${e.message} | Method: ${method} | RESP: ${JSON.stringify(params, null, 2)}`);
				Logger.log(JSON.stringify(e, null, 2));
				return jsonRPC2Error(reply, "InternalError", id, e.message);
			}
		} else {
			return jsonRPC2Error(reply, 'MethodNotFound', id, `Invalid method: ${method}`);
		}
	});
}
