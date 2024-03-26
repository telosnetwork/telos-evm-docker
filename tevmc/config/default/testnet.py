#!/usr/bin/env python3

daemon = {
    'port': 12321
}

redis = {
    'name': 'redis',
    'docker_path': 'redis',
    'tag': 'tevm:redis',
    'host': '127.0.0.1',
    'port': 6379,
    'conf_dir': 'config',
    'data_dir': 'data'
}

elasticsearch = {
    'name': 'elasticsearch',
    'docker_path': 'elasticsearch',
    'tag': 'tevm:elasticsearch',
    'protocol':  'http',
    'host': '127.0.0.1:9200',
    'elastic_pass': 'password',
    'user': 'hyper',
    'pass': 'password',
    'data_dir': 'data'
}

kibana = {
    'name': 'kibana',
    'docker_path': 'kibana',
    'tag': 'tevm:kibana',
    'host': '0.0.0.0',
    'port': 5601,
    'conf_dir': 'config',
    'data_dir': 'data'
}

nodeos = {
    'name': 'nodeos',
    'tag': 'tevm:nodeos-4.0.4-evm',
    'docker_path': 'leap',
    'data_dir_guest': '/mnt/dev/data',
    'data_dir_host': 'data',
    'conf_dir': 'config',
    'contracts_dir': 'contracts',
    'genesis': 'testnet',
    'snapshot': '/telos-testnet-snapshot-evm-deploy.bin',
    'v2_api': 'https://testnet.telos.net',
    'nodeos_bin': 'nodeos',
    'chain_id': '1eaa0824707c8c16bd25145493bf062aecddfeb56c736f6ba6397f3195f33c9f',
    'ini': {
        'wasm_runtime': 'eos-vm-jit',
        'vm_oc_compile_threads': 4,
        'vm_oc_enable': True,

        'chain_state_size': 65536,
        'abi_serializer_max_time': 2000000,
        'account_queries': True,

        'http_addr': '0.0.0.0:8888',
        'allow_origin': '*',
        'http_verbose_error': True,
        'contracts_console': True,
        'http_validate_host': False,
        'p2p_addr': '0.0.0.0:9876',
        'p2p_max_nodes': 100,

        'agent_name': 'Telos Testnet',


        'history_endpoint': '0.0.0.0:29999',
        'trace_history': True,
        'chain_history': True,
        'history_debug_mode': True,
        'history_dir': 'state-history',

        'sync_fetch_span': 1600,

        'max_clients': 250,
        'cleanup_period': 30,
        'txn_blok_lag': 0,
        'allowed_connection': 'any',
        'http_max_response_time': 100000,
        'http_max_body_size': 10000000,

        'enable_stale_production': False,

        'disable_subjective_billing': True,
        'max_transaction_time': 500,

        'plugins': [
            'eosio::http_plugin',
            'eosio::producer_plugin',
            'eosio::chain_api_plugin',
            'eosio::state_history_plugin'
        ],
        'peers': [
            'testnet2.telos.eosusa.news:59877',
            'node1.testnet.telosglobal.io:9876',
            'basho.eos.barcelona:9899',
            'sslapi.teloscentral.com:9875',
            '145.239.133.188:5566',
            'testnet.telos.eclipse24.io:6789',
            'p2p.telos.testnet.detroitledger.tech:30001',
            'basho-p2p.telosuk.io:19876',
            'telos-testnet.atticlab.net:7876',
            'testnet.eossweden.eu:8022',
            'testnet.telos.cryptosuvi.io:2223',
            'p2p-test.tlos.goodblock.io:9876',
            'telosapi.eosmetal.io:59877',
            '207.148.6.75:9877',
            'telosgermany-testnet.genereos.io:9876',
            '176.9.86.214:9877',
            'peer1-telos-testnet.eosphere.io:9876',
            'testnet.telos.africa:9875',
            'p2p.testnet.telosgreen.com:9876',
            'testnet2p2p.telosarabia.net:9876',
            '157.230.29.117:9876',
            'test.telos.kitchen:9876',
            'prod.testnet.bp.teleology.world:9876',
            'telos-testnet.eoscafeblock.com:9879',
            'p2p.basho.telos.dutcheos.io:7654',
            'testnet-b.telos-21zephyr.com:9876',
            'p2p.testnet.telosunlimited.io:9876',
            'peer.tlostest.alohaeos.com:9876',
            '52.175.222.202:9877',
            'testnet2.telos.eosindex.io:9876',
            'basho.sofos.network:9876',
            '85.152.18.129:39876',
            'telostestnet.ikuwara.com:9876',
            'p2p.testnet.nytelos.com:8012',
            'telos.basho.eosdublin.io:9876',
            'telos-testnet.cryptolions.io:9871',
            'api.basho.eostribe.io:9880',
            'p2p-telos-testnet.hkeos.com:59876',
            't-seed.teloskorea.com:19876',
            'telos.testnet.boid.animus.is:3535',
            'telos.testnet.boid.animus.is:5050',
            'kandaweather-testnet.ddns.net:8765',
            'telos-testnet.eosio.cr:9879',
            'testnet.dailytelos.net:9877',
            'testnet.telos.goodblock.io:9876'
        ],
        'subst': 'http://evmwasms.s3.amazonaws.com/subst.json'
    }
}

beats = {
    'name': 'beats',
    'tag': 'tevm:beats',
    'docker_path': 'beats',
    'conf_dir': 'config',
    'data_dir': 'data'
}

telosevm_translator = {
    'name': 'telosevm-translator',
    'tag': 'tevm:telosevm-translator',
    'docker_path': 'telosevm-translator',
    'start_block': 136393814,
    'evm_block_delta': 57,
    'evm_validate_hash': '',
    'stop_block': -1,
    'prev_hash': '8e149fd918bad5a4adfe6f17478e46643f7db7292a2b7b9247f48dc85bdeec94',
    'worker_amount': 4,
    'elastic_dump_size': 4096,
    'elastic_timeout': 1000 * 20,
    'elastic_docs_per_index': 1e7
}

telos_evm_rpc = {
    'name': 'telos-evm-rpc',
    'tag': 'tevm:telos-evm-rpc',
    'docker_path': 'telos-evm-rpc',
    'conf_dir': 'config',
    'chain_id': 41,
    'debug': True,
    'api_host': '0.0.0.0',
    'api_port': 7000,
    'remote_endpoint': 'https://testnet.telos.net/evm',
    'signer_account': 'rpc.evm',
    'signer_permission': 'active',
    'signer_key': '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',
    'contracts': {
        'main': 'eosio.evm'
    },
    'indexer_websocket_host': '0.0.0.0',
    'indexer_websocket_port': '7300',
    'indexer_websocket_uri': 'ws://127.0.0.1:7300/evm',
    'rpc_websocket_host': '0.0.0.0',
    'rpc_websocket_port': '7400',
    'elastic_prefix': 'telos-testnet-tevmc',
    'elasitc_index_version': 'v1.5'
}

default_config = {
    'daemon': daemon,

    'redis': redis,
    'elasticsearch': elasticsearch,
    'kibana': kibana,
    'nodeos': nodeos,
    'beats': beats,
    'telosevm-translator': telosevm_translator,
    'telos-evm-rpc': telos_evm_rpc
}
