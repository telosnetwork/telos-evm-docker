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
Object.defineProperty(exports, "__esModule", { value: true });
exports.autoPrefix = void 0;
const common_functions_1 = require("../../../../../helpers/common_functions");
const BN = require('bn.js');
const abiDecoder = require("abi-decoder");
const abi = require("ethereumjs-abi");
function numToHex(input) {
    if (typeof input === 'number') {
        return '0x' + input.toString(16);
    }
    else {
        return '0x' + (parseInt(input, 10)).toString(16);
    }
}
function jsonRcp2Error(reply, type, requestId, message, code) {
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
    return {
        jsonrpc: "2.0",
        id: requestId,
        error: {
            code: errorCode,
            message
        }
    };
}
function default_1(fastify, opts) {
    return __awaiter(this, void 0, void 0, function* () {
        const methods = new Map();
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
        function searchActionByHash(trxHash) {
            var _a, _b, _c;
            return __awaiter(this, void 0, void 0, function* () {
                try {
                    let _hash = trxHash.toLowerCase();
                    if (_hash.startsWith("0x")) {
                        _hash = _hash.slice(2);
                    }
                    const results = yield fastify.elastic.search({
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
                    return (_c = (_b = (_a = results === null || results === void 0 ? void 0 : results.body) === null || _a === void 0 ? void 0 : _a.hits) === null || _b === void 0 ? void 0 : _b.hits[0]) === null || _c === void 0 ? void 0 : _c._source;
                }
                catch (e) {
                    console.log(e);
                    return null;
                }
            });
        }
        function searchDeltasByHash(trxHash) {
            var _a, _b, _c;
            return __awaiter(this, void 0, void 0, function* () {
                try {
                    let _hash = trxHash.toLowerCase();
                    if (_hash.startsWith("0x")) {
                        _hash = _hash.slice(2);
                    }
                    const results = yield fastify.elastic.search({
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
                    return (_c = (_b = (_a = results === null || results === void 0 ? void 0 : results.body) === null || _a === void 0 ? void 0 : _a.hits) === null || _b === void 0 ? void 0 : _b.hits[0]) === null || _c === void 0 ? void 0 : _c._source;
                }
                catch (e) {
                    console.log(e);
                    return null;
                }
            });
        }
        function buildLogsObject(logs, blHash, blNumber, txHash, txIndex) {
            const _logs = [];
            if (logs) {
                let counter = 0;
                for (const log of logs) {
                    _logs.push({
                        address: log.address,
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
        function reconstructBlockFromReceipts(receipts, full) {
            var _a, _b;
            return __awaiter(this, void 0, void 0, function* () {
                let actions = [];
                if (receipts.length > 0) {
                    const rawResults = yield fastify.elastic.search({
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
                    actions = (_b = (_a = rawResults === null || rawResults === void 0 ? void 0 : rawResults.body) === null || _a === void 0 ? void 0 : _a.hits) === null || _b === void 0 ? void 0 : _b.hits;
                }
                let blockHash;
                let blockHex;
                let timestamp;
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
                    }
                    else {
                        const txRawAction = actions.find(a => {
                            return a._source['@raw']['hash'] === "0x" + receipt['hash'];
                        });
                        if (txRawAction) {
                            const rawAction = txRawAction._source['@raw'];
                            trxs.push({
                                blockHash: blockHash,
                                blockNumber: blockHex,
                                from: rawAction['from'],
                                gas: receipt['gasused'],
                                gasPrice: "0x" + Number(rawAction['gas_price']).toString(16),
                                hash: "0x" + receipt['hash'],
                                input: rawAction['input_data'],
                                nonce: "0x" + Number(rawAction['nonce']).toString(16),
                                to: rawAction['to'],
                                transactionIndex: "0x" + Number(receipt['trx_index']).toString(16),
                                value: "0x0"
                            });
                        }
                    }
                }
                if (trxs.length > 0) {
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
                        timestamp: "0x" + (timestamp === null || timestamp === void 0 ? void 0 : timestamp.toString(16)),
                        totalDifficulty: "0x0",
                        transactions: trxs,
                        transactionsRoot: NULL_HASH,
                        uncles: []
                    };
                }
                else {
                    return null;
                }
            });
        }
        function getDeltasByTerm(term, value) {
            var _a, _b;
            return __awaiter(this, void 0, void 0, function* () {
                const termStruct = {};
                termStruct[term] = value;
                const results = yield fastify.elastic.search({
                    index: `${fastify.manager.chain}-delta-*`,
                    size: 1000,
                    body: { query: { bool: { must: [{ term: termStruct }] } } }
                });
                return (_b = (_a = results === null || results === void 0 ? void 0 : results.body) === null || _a === void 0 ? void 0 : _a.hits) === null || _b === void 0 ? void 0 : _b.hits;
            });
        }
        function getCurrentBlockNumber() {
            return __awaiter(this, void 0, void 0, function* () {
                const global = yield fastify.eosjs.rpc.get_table_rows({
                    code: "eosio",
                    scope: "eosio",
                    table: "global",
                    json: true
                });
                const head_block_num = parseInt(global.rows[0].block_num, 10);
                return '0x' + head_block_num.toString(16);
            });
        }
        function toBlockNumber(blockParam) {
            return __awaiter(this, void 0, void 0, function* () {
                console.log("toBlockNumber caleld with " + blockParam);
                if (blockParam == "latest" || blockParam == "pending")
                    return yield getCurrentBlockNumber();
                if (blockParam == "earliest")
                    return "0x0";
                return blockParam;
            });
        }
        // LOAD METHODS
        /**
         * Returns true if client is actively listening for network connections.
         */
        methods.set('net_listening', () => true);
        /**
         * Returns the current "latest" block number.
         */
        methods.set('eth_blockNumber', () => __awaiter(this, void 0, void 0, function* () {
            try {
                return yield getCurrentBlockNumber();
            }
            catch (e) {
                throw new Error('Request Failed: ' + e.message);
            }
        }));
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
        methods.set('eth_getTransactionCount', ([address]) => __awaiter(this, void 0, void 0, function* () {
            return yield fastify.evm.telos.getNonce(address.toLowerCase());
        }));
        /**
         * Returns the compiled smart contract code,
         * if any, at a given address.
         */
        methods.set('eth_getCode', ([address]) => __awaiter(this, void 0, void 0, function* () {
            try {
                const account = yield fastify.evm.telos.getEthAccount(address.toLowerCase());
                if (account.code && account.code.length > 0) {
                    return "0x" + Buffer.from(account.code).toString("hex");
                }
                else {
                    return "0x0000";
                }
            }
            catch (e) {
                return "0x0000";
            }
        }));
        /**
         * Returns the value from a storage position at a given address.
         */
        methods.set('eth_getStorageAt', ([address, position]) => __awaiter(this, void 0, void 0, function* () {
            return yield fastify.evm.telos.getStorageAt(address.toLowerCase(), position);
        }));
        /**
         * Generates and returns an estimate of how much gas is necessary to
         * allow the transaction to complete.
         */
        methods.set('eth_estimateGas', ([txParams, block]) => __awaiter(this, void 0, void 0, function* () {
            const encodedTx = yield fastify.evm.createEthTx(Object.assign(Object.assign({}, txParams), { sender: txParams.from, gasPrice: 10000000000000000, gasLimit: 10000000000000000 }));
            const gas = yield fastify.evm.telos.estimateGas({
                account: opts.signer_account,
                ram_payer: fastify.evm.telos.telosContract,
                tx: encodedTx,
                sender: txParams.from,
            });
            return `0x${Math.ceil((parseInt(gas, 16) * GAS_OVER_ESTIMATE_MULTIPLIER)).toString(16)}`;
        }));
        /**
         * Returns the current gas price in wei.
         */
        methods.set('eth_gasPrice', () => __awaiter(this, void 0, void 0, function* () {
            let price = yield fastify.evm.telos.getGasPrice();
            let priceInt = parseInt(price, 10);
            return isNaN(priceInt) ? null : formatQuantity(priceInt.toString(16));
        }));
        /**
         * Returns the balance of the account of given address.
         */
        methods.set('eth_getBalance', ([address]) => __awaiter(this, void 0, void 0, function* () {
            try {
                const account = yield fastify.evm.telos.getEthAccount(address.toLowerCase());
                const bal = account.balance;
                return "0x" + bal.toString(16);
            }
            catch (e) {
                return "0x0000";
            }
        }));
        /**
         * Returns the balance in native tokens (human readable format)
         * of the account of given address.
         */
        methods.set('eth_getBalanceHuman', ([address]) => __awaiter(this, void 0, void 0, function* () {
            try {
                const account = yield fastify.evm.telos.getEthAccount(address.toLowerCase());
                const bal = account.balance;
                // @ts-ignore
                const balConverted = bal / decimalsBN;
                return balConverted.toString(10);
            }
            catch (e) {
                return "0";
            }
        }));
        /**
         * Executes a new message call immediately without creating a
         * transaction on the block chain.
         */
        methods.set('eth_call', ([txParams]) => __awaiter(this, void 0, void 0, function* () {
            if (chainIds.includes(opts.chainId) && chainAddr.includes(txParams.to)) {
                const { params: [users, tokens] } = abiDecoder.decodeMethod(txParams.data);
                if (tokens.value.length === 1 && tokens.value[0] === zeros) {
                    const balances = yield Promise.all(users.value.map((user) => {
                        return methods.get('eth_getBalance')([user, null]);
                    }));
                    return "0x" + abi.rawEncode(balances.map(() => "uint256"), balances).toString("hex");
                }
            }
            let _value = new BN(0);
            if (txParams.value) {
                _value = new BN(Buffer.from(txParams.value.slice(2), "hex"));
            }
            const obj = Object.assign(Object.assign({}, txParams), { value: _value, sender: txParams.from });
            const encodedTx = yield fastify.evm.createEthTx(obj);
            const output = yield fastify.evm.telos.call({
                account: opts.signer_account,
                tx: encodedTx,
                sender: txParams.from,
            });
            return "0x" + output;
        }));
        /**
         * Submits a pre-signed transaction for broadcast to the
         * Ethereum network.
         */
        methods.set('eth_sendRawTransaction', ([signedTx]) => __awaiter(this, void 0, void 0, function* () {
            try {
                const rawData = yield fastify.evm.telos.raw({
                    account: opts.signer_account,
                    tx: signedTx
                });
                return '0x' + rawData.eth.transactionHash;
            }
            catch (e) {
                console.log(e);
                return null;
            }
        }));
        /**
         * Submits transaction for broadcast to the Ethereum network.
         */
        methods.set('eth_sendTransaction', ([txParams]) => __awaiter(this, void 0, void 0, function* () {
            const buf = Buffer.from(txParams.value.slice(2), "hex");
            const encodedTx = yield fastify.evm.createEthTx(Object.assign(Object.assign({}, txParams), { value: new BN(buf), rawSign: true, sender: txParams.from }));
            try {
                const rawData = yield fastify.evm.telos.raw({
                    account: opts.signer_account,
                    ram_payer: fastify.evm.telos.telosContract,
                    tx: encodedTx
                });
                return "0x" + rawData.eth.transactionHash;
            }
            catch (e) {
                console.log(e);
                return null;
            }
        }));
        /**
         * Returns the receipt of a transaction by transaction hash.
         */
        methods.set('eth_getTransactionReceipt', ([trxHash]) => __awaiter(this, void 0, void 0, function* () {
            if (trxHash) {
                // lookup receipt delta
                const receiptDelta = yield searchDeltasByHash(trxHash);
                if (!receiptDelta)
                    return null;
                const receipt = receiptDelta['@evmReceipt'];
                // lookup raw action
                const rawAction = yield searchActionByHash(trxHash);
                if (!rawAction)
                    return null;
                const raw = rawAction['@raw'];
                const _blockHash = '0x' + receipt['block_hash'];
                const _blockNum = numToHex(receipt['block']);
                const _gas = '0x' + receipt['gasused'].toString(16);
                let _contractAddr = null;
                if (receipt['createdaddr']) {
                    _contractAddr = '0x' + receipt['createdaddr'];
                }
                return {
                    blockHash: _blockHash,
                    blockNumber: numToHex(receipt['block']),
                    contractAddress: _contractAddr,
                    cumulativeGasUsed: _gas,
                    from: raw['from'],
                    gasUsed: _gas,
                    logsBloom: null,
                    status: numToHex(receipt['status']),
                    to: raw['to'],
                    transactionHash: raw['hash'],
                    transactionIndex: numToHex(receipt['trx_index']),
                    logs: buildLogsObject(receipt['logs'], _blockHash, _blockNum, raw['hash'], numToHex(receipt['trx_index'])),
                    errors: receipt['errors'],
                    output: '0x' + receipt['output']
                };
            }
            else {
                return null;
            }
        }));
        /**
         * Returns information about a transaction for a given hash.
         */
        methods.set('eth_getTransactionByHash', ([trxHash]) => __awaiter(this, void 0, void 0, function* () {
            // lookup raw action
            const rawAction = yield searchActionByHash(trxHash);
            if (!rawAction)
                return null;
            const raw = rawAction['@raw'];
            // lookup receipt delta
            const receiptDelta = yield searchDeltasByHash(trxHash);
            if (!receiptDelta)
                return null;
            const receipt = receiptDelta['@evmReceipt'];
            const _blockHash = '0x' + receipt['block_hash'];
            const _blockNum = numToHex(receipt['block']);
            return {
                blockHash: _blockHash,
                blockNumber: _blockNum,
                from: raw['from'],
                gas: numToHex(raw.gas_limit),
                gasPrice: numToHex(raw.gas_price),
                hash: raw['hash'],
                input: raw['input_data'],
                nonce: numToHex(raw['nonce']),
                // "r": "0x2a378831cf81d99a3f06a18ae1b6ca366817ab4d88a70053c41d7a8f0368e031",
                // "s": "0x450d831a05b6e418724436c05c155e0a1b7b921015d0fbc2f667aed709ac4fb5",
                to: raw['to'],
                transactionIndex: numToHex(receipt['trx_index']),
                // "v": "0x25",
                value: numToHex(raw['value'])
            };
        }));
        /**
         * Returns information about a block by number.
         */
        methods.set('eth_getBlockByNumber', ([block, full]) => __awaiter(this, void 0, void 0, function* () {
            const blockNumber = parseInt(yield toBlockNumber(block), 16);
            const receipts = yield getDeltasByTerm("@evmReceipt.block", blockNumber);
            return yield reconstructBlockFromReceipts(receipts, full);
        }));
        /**
         * Returns information about a block by hash.
         */
        methods.set('eth_getBlockByHash', ([hash, full]) => __awaiter(this, void 0, void 0, function* () {
            let _hash = hash.toLowerCase();
            if (_hash.startsWith("0x")) {
                _hash = _hash.slice(2);
            }
            const receipts = yield getDeltasByTerm("@evmReceipt.block_hash", _hash);
            return yield reconstructBlockFromReceipts(receipts, full);
        }));
        /**
         * Returns the number of transactions in the block with
         * the given block hash.
         */
        methods.set('eth_getBlockTransactionCountByHash', ([hash]) => __awaiter(this, void 0, void 0, function* () {
            let _hash = hash.toLowerCase();
            if (_hash.startsWith("0x")) {
                _hash = _hash.slice(2);
            }
            const receipts = yield getDeltasByTerm("@evmReceipt.block_hash", _hash);
            const txCount = receipts.length;
            return '0x' + txCount.toString(16);
        }));
        /**
         * Returns the number of transactions in the block with
         * the given block number.
         */
        methods.set('eth_getBlockTransactionCountByNumber', ([block]) => __awaiter(this, void 0, void 0, function* () {
            const blockNumber = parseInt(block, 16);
            const receipts = yield getDeltasByTerm("@evmReceipt.block", blockNumber);
            const txCount = receipts.length;
            return '0x' + txCount.toString(16);
        }));
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
        methods.set('eth_getLogs', (params) => __awaiter(this, void 0, void 0, function* () {
            // query preparation
            let address = params.address;
            let topics = params.topics;
            let fromBlock = params.fromBlock;
            let toBlock = params.toBlock;
            let blockHash = params.blockHash;
            const queryBody = {
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
                queryBody.bool.must.push({ term: { "@evmReceipt.block_hash": blockHash } });
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
                queryBody.bool.must.push({ term: { "@evmReceipt.logs.address": address } });
            }
            if (topics && topics.length > 0) {
                // console.log(`getLogs using topics:\n${topics}`);
                queryBody.bool.must.push({
                    terms: {
                        "@evmReceipt.logs.topics": topics.map(topic => {
                            return topic.startsWith('0x') ? topic.slice(2).toLowerCase() : topic.toLowerCase();
                        })
                    }
                });
            }
            // search
            try {
                const searchResults = yield fastify.elastic.search({
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
            }
            catch (e) {
                console.log(JSON.stringify(e, null, 2));
                return [];
            }
        }));
        // END METHODS
        /**
         * Main JSON RPC 2.0 Endpoint
         */
        fastify.post('/', (request, reply) => __awaiter(this, void 0, void 0, function* () {
            const { jsonrpc, id, method, params } = request.body;
            if (jsonrpc !== "2.0") {
                return jsonRcp2Error(reply, "InvalidRequest", id, "Invalid JSON RPC");
            }
            if (methods.has(method)) {
                const tRef = process.hrtime.bigint();
                const func = methods.get(method);
                try {
                    const result = yield func(params);
                    let origin;
                    if (request.headers['origin'] === METAMASK_EXTENSION_ORIGIN) {
                        origin = 'MetaMask';
                    }
                    else {
                        if (request.headers['origin']) {
                            origin = request.headers['origin'];
                        }
                        else {
                            origin = request.headers['user-agent'];
                        }
                    }
                    const _usage = reply.getHeader('x-ratelimit-remaining');
                    const _limit = reply.getHeader('x-ratelimit-limit');
                    const _ip = request.headers['x-real-ip'];
                    const duration = ((Number(process.hrtime.bigint()) - Number(tRef)) / 1000).toFixed(3);
                    common_functions_1.hLog(`${new Date().toISOString()} - ${duration} μs - ${_ip} (${_usage}/${_limit}) - ${origin} - ${method}`);
                    console.log(`REQ: ${JSON.stringify(params)} | RESP: ${result}`);
                    reply.send({ id, jsonrpc, result });
                }
                catch (e) {
                    common_functions_1.hLog(e.message, method, JSON.stringify(params, null, 2));
                    console.log(JSON.stringify(e, null, 2));
                    return jsonRcp2Error(reply, "InternalError", id, e.message);
                }
            }
            else {
                return jsonRcp2Error(reply, 'MethodNotFound', id, `Invalid method: ${method}`);
            }
        }));
    });
}
exports.default = default_1;
exports.autoPrefix = '/evm';
//# sourceMappingURL=index.js.map