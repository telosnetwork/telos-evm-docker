import {FastifyInstance, FastifyReply, FastifyRequest} from "fastify";
import {TelosEvmConfig} from "../../index";

const schema: any = {
	summary: 'DEPRECATED: Used by explorer but to be replaced by /v2/evm/get_transactions',
	tags: ['evm'],
};

export default async function (fastify: FastifyInstance, opts: TelosEvmConfig) {
	fastify.get('/evm_explorer/get_transactions', { schema }, async (request: FastifyRequest, reply: FastifyReply) => {

		let address = request.query["address"];
		if (address) {
			if (!address.startsWith('0x')) {
				address = '0x' + address;
			}
			address = address.toLowerCase();
		} else {
			throw new Error('missing address');
		}

		const tref = Date.now();

		const _transactions = [];
		const txHashes = [];
		let totalCount = 0;
		let fromCounter = 0;
		let toCounter = 0;

		const searchResults = await fastify.elastic.search({
			index: `${fastify.manager.chain}-action-*`,
			body: {
				track_total_hits: true,
				size: 100,
				sort: [{global_sequence: {order: "desc"}}],
				query: {
					bool: {
						should: [
							{term: {"@raw.from": address}},
							{term: {"@raw.to": address}}
						]
					}
				}
			}
		});

		if (searchResults.body && searchResults.body?.hits?.hits.length > 0) {

			totalCount = searchResults.body.hits.total.value;

			for (const hit of searchResults.body?.hits?.hits) {
				const result = hit._source;
				if (result['@raw']) {
					const txHash: string = result['@raw']['hash'];

					txHashes.push(txHash.slice(2));

					if (result['@raw'].to === address) {
						toCounter++;
					}

					if (result['@raw'].from === address) {
						fromCounter++;
					}

					_transactions.push({
						...result['@raw'],
						trx_id: result['trx_id'],
						block_num: result['block_num'],
						'@timestamp': result['@timestamp']
					});
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
	});
}
