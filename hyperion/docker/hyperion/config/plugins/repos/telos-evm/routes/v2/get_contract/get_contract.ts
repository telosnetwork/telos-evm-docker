import {FastifyInstance, FastifyReply, FastifyRequest} from "fastify";
import {timedQuery} from "../../../../../../api/helpers/functions";

async function getContract(fastify: FastifyInstance, request: FastifyRequest) {

	const query: any = request.query;

	let contract = query.contract.replace(/^0x/, '').replace(/^0*/, '');
	const response = {
		creation_trx: '',
		creator: '',
		abi: '',
		timestamp: '',
		block_num: 0
	};

	const results = await fastify.elastic.search({
		"index": fastify.manager.chain + '-delta-*',
		"body": {
			size: 1,
			query: {
				bool: {
					must: [{term: {"@evmReceipt.createdaddr": contract}}]
				}
			}
		}
	});

	if (results['body']['hits']['hits'].length === 1) {
		const result = results['body']['hits']['hits'][0]._source['@evmReceipt'];
		response.creation_trx = `0x${result.hash}`;
		response.block_num = result.block;
		// TODO: pull the rest of the values and populate them here, likely after the index refactor where it will already be here
		return response;
	} else {
		// TODO: maybe lookup if this is even a contract?
		throw new Error("contract deployment not found");
	}
}

export function getContractHandler(fastify: FastifyInstance, route: string) {
	return async (request: FastifyRequest, reply: FastifyReply) => {
		reply.send(await timedQuery(getContract, fastify, request, route));
	}
}
