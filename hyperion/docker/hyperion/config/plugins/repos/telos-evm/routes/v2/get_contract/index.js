"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const get_contract_1 = require("./get_contract");
const functions_1 = require("../../../../../../../api/helpers/functions");
function default_1(fastify, opts, next) {
    const schema = {
        summary: 'get contract info',
        tags: ['evm'],
        querystring: {
            type: 'object',
            properties: {
                "contract": {
                    description: 'contract address',
                    type: 'string',
                    minLength: 42,
                    maxLength: 42
                }
            },
            required: ["contract"]
        },
        response: functions_1.extendResponseSchema({
            "creation_trx": {
                type: "string"
            },
            "creator": {
                type: "string"
            },
            "timestamp": {
                type: "string"
            },
            "block_num": {
                type: "integer"
            },
            "abi": {
                type: "string"
            },
        })
    };
    functions_1.addApiRoute(fastify, 'GET', functions_1.getRouteName(__filename), get_contract_1.getContractHandler, schema);
    next();
}
exports.default = default_1;
//# sourceMappingURL=index.js.map