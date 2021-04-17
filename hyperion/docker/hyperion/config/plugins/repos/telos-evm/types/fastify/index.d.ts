import {Client} from "@elastic/elasticsearch";
import {Redis} from "ioredis";
import {ConnectionManager} from "../../../../../connections/manager.class";
import {Api, JsonRpc} from "eosjs";

interface EOSJS {
	rpc: JsonRpc,
	api: Api
}

declare module 'fastify' {
	export interface FastifyInstance {
		manager: ConnectionManager;
		redis: Redis;
		elastic: Client;
		chain_api: string;
		push_api: string;
		evm: any;
		eosjs: EOSJS;
	}
}
