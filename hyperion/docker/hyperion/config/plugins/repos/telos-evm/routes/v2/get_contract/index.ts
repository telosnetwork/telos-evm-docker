import {FastifyInstance, FastifySchema} from "fastify";
import {getContractHandler} from "./get_contract";
import {addApiRoute, getRouteName} from "../../../../../../api/helpers/functions";

export default function (fastify: FastifyInstance, opts: any, next) {
	const schema: any = {
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
		response: {
			200: {
				description: "Success",
				type: "object",
				properties: {
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
				}
			}
		}
	};
	addApiRoute(fastify, 'GET', 'v2/evm/get_contract', getContractHandler, schema);
	next();
}