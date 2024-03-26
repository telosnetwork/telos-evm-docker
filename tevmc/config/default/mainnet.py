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
    'genesis': 'mainnet',
    'snapshot': '/telos-mainnet-snapshot-evm-deploy.bin',
    'v2_api': 'https://mainnet.telos.net',
    'nodeos_bin': 'nodeos',
    'chain_id': '4667b205c6838ef70ff7988f6e8257e8be0e1284a2f59699054a018f743b1d11',
    'ini': {
        'wasm_runtime': 'eos-vm-jit',
        'vm_oc_compile_threads': 4,
        'vm_oc_enable': True,

        'chain_state_size': 65536,
        'account_queries': True,
        'abi_serializer_max_time': 2000000,
        'http_max_response_time': 100000,

        'http_addr': '0.0.0.0:8888',
        'allow_origin': '*',
        'http_verbose_error': True,
        'contracts_console': True,
        'http_validate_host': False,
        'p2p_addr': '0.0.0.0:9876',
        'p2p_max_nodes': 1,

        'agent_name': 'Telos Mainnet',

        'history_endpoint': '0.0.0.0:29999',
        'trace_history': True,
        'chain_history': True,
        'history_debug_mode': True,
        'history_dir': 'state-history',

        'sync_fetch_span': 2000,

        'max_clients': 250,

        'disable_subjective_billing': True,
        'max_transaction_time': 500,

        'plugins': [
            'eosio::http_plugin',
            'eosio::chain_api_plugin',
            'eosio::state_history_plugin'
        ],
        'peers': [
            'telosp2p.actifit.io:9876',
            'telos.eu.eosamsterdam.net:9120',
            'p2p.telos.eosargentina.io:9879',
            'telos.p2p.boid.animus.is:5151',
            'telos.p2p.boid.animus.is:5252',
            'p2p.telos.y-knot.io:9877',
            'telos.caleos.io:9880',
            'p2p.creativblock.org:9876',
            'p2p.telos.cryptobloks.io:9876',
            'telos.cryptolions.io:9871',
            'p2p.dailytelos.net:9876',
            'p2p.telos.detroitledger.tech:1337',
            'node-telos.eosauthority.com:10311',
            'telosp2p.eos.barcelona:2095',
            'peer1-telos.eosphere.io:9876',
            'peer2-telos.eosphere.io:9876',
            'telos.eosrio.io:8092',
            'api.telos.cryptotribe.io:7876',
            'telos.p2p.eosusa.io:9876',
            'telos.eosvenezuela.io:9871',
            'p2p.fortisbp.io:9876',
            'mainnet.telos.goodblock.io:9879',
            'seed-telos.infinitybloc.io:9877',
            'p2p.kainosbp.com:9876',
            'kandaweather-mainnet.ddns.net:9876',
            'tlos-p2p.katalyo.com:11877',
            'telos.seed.eosnation.io:9876',
            'p2p.telos.nodenode.org:9876',
            'p2p.telos.pandabloks.com:9876',
            'mainnet.persiantelos.com:8880',
            'telosp2p.sentnl.io:4242',
            'p2p.telos.africa:9877',
            'telos.eossweden.eu:8012',
            'telos.greymass.com:19871',
            'peers.teleology.one:9876',
            'telos.teleology.one:9876',
            'p2p.telosarabia.net:9876',
            'sslapi.teloscentral.com:9876',
            'testnet.telosculture.com:9874',
            'p2p.telosgermany.genereos.io:9876',
            'node1.us-east.telosglobal.io:9876',
            'node1.us-west.telosglobal.io:9876',
            'p2p2.telos.telosgreen.com:9877',
            'p2p.telos.blocksindia.com:9876',
            'api.telos.kitchen:9876',
            'seed.teloskorea.com:9876',
            'seed.telosmadrid.io:9877',
            'p2p.telosuk.io:9876',
            'p2p.telosunlimited.io:9876',
            'telosyouth.io:9876',
            'p2p.theteloscope.io:9876',
            'mainnet.teloscrew.com:18876',
            '136.243.90.53:9876',
            'p2p.telos.dutcheos.io:9876',
            'p2p.telos.zenblocks.io:9876'
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
    'start_block': 180698860,
    'evm_block_delta': 36,
    'evm_validate_hash': '',
    'stop_block': -1,
    'prev_hash': 'cfa67996f5d4f1e9e2b8b13a8984e1d8997091060748c3345f160b39050809b6',
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
    'chain_id': 40,
    'debug': True,
    'api_host': '0.0.0.0',
    'api_port': 7000,
    'remote_endpoint': 'https://mainnet.telos.net/evm',
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
    'elastic_prefix': 'telos-mainnet-tevmc',
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

