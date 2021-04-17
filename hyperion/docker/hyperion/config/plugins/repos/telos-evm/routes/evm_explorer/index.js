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
function default_1(fastify, opts) {
    return __awaiter(this, void 0, void 0, function* () {
        fastify.get('/get_transactions', (request, reply) => __awaiter(this, void 0, void 0, function* () {
            var _a, _b, _c, _d, _e, _f, _g, _h;
            let address = request.query["address"];
            if (address) {
                if (!address.startsWith('0x')) {
                    address = '0x' + address;
                }
                address = address.toLowerCase();
            }
            else {
                throw new Error('missing address');
            }
            const tref = Date.now();
            const _transactions = [];
            const txHashes = [];
            let totalCount = 0;
            let fromCounter = 0;
            let toCounter = 0;
            const searchResults = yield fastify.elastic.search({
                index: `${fastify.manager.chain}-action-*`,
                body: {
                    track_total_hits: true,
                    size: 100,
                    sort: [{ global_sequence: { order: "desc" } }],
                    query: {
                        bool: {
                            should: [
                                { term: { "@raw.from": address } },
                                { term: { "@raw.to": address } }
                            ]
                        }
                    }
                }
            });
            if (searchResults.body && ((_b = (_a = searchResults.body) === null || _a === void 0 ? void 0 : _a.hits) === null || _b === void 0 ? void 0 : _b.hits.length) > 0) {
                totalCount = searchResults.body.hits.total.value;
                for (const hit of (_d = (_c = searchResults.body) === null || _c === void 0 ? void 0 : _c.hits) === null || _d === void 0 ? void 0 : _d.hits) {
                    const result = hit._source;
                    if (result['@raw']) {
                        const txHash = result['@raw']['hash'];
                        txHashes.push(txHash.slice(2));
                        if (result['@raw'].to === address) {
                            toCounter++;
                        }
                        if (result['@raw'].from === address) {
                            fromCounter++;
                        }
                        _transactions.push(Object.assign(Object.assign({}, result['@raw']), { trx_id: result['trx_id'], block_num: result['block_num'], '@timestamp': result['@timestamp'] }));
                    }
                }
                const receiptsResults = yield fastify.elastic.search({
                    index: `${fastify.manager.chain}-delta-*`,
                    body: {
                        size: 1000,
                        query: {
                            bool: {
                                must: [
                                    { terms: { "@evmReceipt.hash": txHashes } }
                                ]
                            }
                        }
                    }
                });
                if (receiptsResults.body && ((_f = (_e = receiptsResults.body) === null || _e === void 0 ? void 0 : _e.hits) === null || _f === void 0 ? void 0 : _f.hits.length) > 0) {
                    const receiptMap = new Map();
                    for (const hit of (_h = (_g = receiptsResults.body) === null || _g === void 0 ? void 0 : _g.hits) === null || _h === void 0 ? void 0 : _h.hits) {
                        const result = hit._source;
                        receiptMap.set('0x' + result['@evmReceipt']['hash'], result['@evmReceipt']);
                    }
                    for (const transaction of _transactions) {
                        if (receiptMap.has(transaction.hash)) {
                            transaction['receipt'] = receiptMap.get(transaction.hash);
                            delete transaction['receipt']['hash'];
                            delete transaction['receipt']['trxid'];
                        }
                    }
                }
            }
            reply.send({
                query_time_ms: Date.now() - tref,
                search_scope: address,
                from_address: fromCounter,
                to_address: toCounter,
                total: totalCount,
                transactions: _transactions,
                more: _transactions.length < totalCount
            });
        }));
    });
}
exports.default = default_1;
exports.autoPrefix = '/evm_explorer';
//# sourceMappingURL=index.js.map