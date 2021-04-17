import {HyperionPlugin} from "../../hyperion-plugin";
import {FastifyInstance, FastifyReply, FastifyRequest} from "fastify";
import {existsSync, readFileSync, unlinkSync, writeFileSync} from "fs";
import {join} from "path";
import fastifyStatic from "fastify-static";
import {ServerResponse} from "http";
import {hLog} from "../../../helpers/common_functions";
import got from "got";

export interface ExplorerConfig {
	chain_logo_url: string;
	server_name: string;
}

export default class Explorer extends HyperionPlugin {
	hasApiRoutes = true;

	pluginConfig: ExplorerConfig;

	constructor(config: ExplorerConfig) {
		super(config);
		if (this.baseConfig) {
			this.pluginConfig = this.baseConfig;
			this.fetchChainLogo().catch(console.log);
		}
	}

	async fetchChainLogo() {
		try {
			if (this.pluginConfig.chain_logo_url) {
				hLog(`Downloading chain logo from ${this.pluginConfig.chain_logo_url}...`);
				const chainLogo = await got(this.pluginConfig.chain_logo_url);
				const path = join(__dirname, 'dist', 'assets', this.chainName + '_logo.png');
				writeFileSync(path, chainLogo.rawBody);
				this.pluginConfig.chain_logo_url = 'https://' + this.pluginConfig.server_name + '/v2/explore/assets/' + this.chainName + '_logo.png';
			}
		} catch (e) {
			hLog(e);
		}
	}

	addRoutes(server: FastifyInstance): void {
		server.register(require('fastify-compress'), {global: false});

		try {
			const _data = readFileSync(join(__dirname, 'hyperion-explorer-plugin', 'src', 'manifest.webmanifest'));
			const tempPath = join(__dirname, 'dist', 'manifest.webmanifest');
			if (existsSync(tempPath)) {
				unlinkSync(tempPath);
			}
			const baseManifest = JSON.parse(_data.toString());
			baseManifest.name = `Hyperion Explorer - ${server.manager.config.api.chain_name}`;
			baseManifest.short_name = baseManifest.name;
			server.get('/v2/explore/manifest.webmanifest', (request: FastifyRequest, reply: FastifyReply) => {
				reply.send(baseManifest);
			});
		} catch (e) {
			console.log(e);
		}


		server.register(fastifyStatic, {
			root: join(__dirname, 'dist'),
			redirect: true,
			wildcard: false,
			prefix: '/v2/explore',
			setHeaders: (res: ServerResponse, path) => {
				if (path.endsWith('/ngsw-worker.js')) {
					res.setHeader('Service-Worker-Allowed', '/');
				}
			}
		});


		server.get('/v2/explore/**/*', (request: FastifyRequest, reply: FastifyReply) => {
			reply.sendFile('index.html', join(__dirname, 'dist'));
		});


		const manager = server.manager;
		const apiConfig = manager.config.api;
		server.get('/v2/explorer_metadata', (request: FastifyRequest, reply: FastifyReply) => {
			reply.send({
				logo: apiConfig.chain_logo_url,
				provider: apiConfig.provider_name,
				provider_url: apiConfig.provider_url,
				chain_name: apiConfig.chain_name,
				chain_id: manager.conn.chains[manager.chain].chain_id,
				custom_core_token: apiConfig.custom_core_token
			});
		});
	}
}
