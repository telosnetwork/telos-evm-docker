#!/usr/bin/env python3

redis = {
    'name': 'redis',
    'tag': 'redis:5.0.14-bullseye',
    'host': 'localhost',
    'port': 6379,
    'data_volume': 'redis_data'
}

rabbitmq = {
    'name': 'rabbitmq',
    'tag': 'rabbitmq:3.9.12-management',
    'host': 'localhost:5672',
    'api': 'localhost:15672',
    'user': 'username',
    'pass': 'password',
    'vhost': '/hyperion',
    'data_volume': 'rabbitmq_data'
}

elasticsearch = {
    'name': 'elasticsearch',
    'tag': 'elasticsearch:7.16.3',
    'protocol':  'http',
    'host': 'localhost:9200',
    'ingest_nodes': ['localhost:9200'],
    'user': 'elastic',
    'pass': 'password',
    'data_volume': 'elasticsearch_data'
}

kibana = {
    'name': 'kibana',
    'tag': 'kibana:7.16.3',
    'port': 5601
}

nodeos = {
    'name': 'nodeos',
    'tag': 'eosio:2.1.0-evm',
    'docker_path': 'eosio',
    'volume': 'eosio_volume',
    'data_dir': '/mnt/dev/data',
    'genesis': 'mainnet',
    'snapshot': '/root/snapshots/snapshot-mainnet-20211026-blk-180635436.bin',
    'log_path': '/root/nodeos.log',
    'data_volume': 'elasticsearch_data',
    'ini': {
        'wasm_runtime': 'eos-vm-jit', 
        'vm_oc_compile_threads': 4,
        'vm_oc_enable': True,

        'chain_state_size': 65536,
        'reversible_blocks_size': 4096,
        'abi_serializer_max_time': 2000000,
        'account_queries': True,

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
        'cleanup_period': 30,
        'txn_blok_lag': 0,
        'allowed_connection': 'any',
        'http_max_response_time': 100000,
        'http_max_body_size': 10000000,

        'enable_stale_production': False,
        
        'sig_provider': 'EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L=KEY:5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',

        'plugins': [
            'eosio::net_plugin',
            'eosio::http_plugin',
            'eosio::chain_plugin',
            'eosio::producer_plugin',
            'eosio::chain_api_plugin',
            'eosio::state_history_plugin'
        ],
        'peers': [
            'p2p.eos.miami:13975',
            'p2p.telos-21zephyr.com:9876',
            'seed.telosmadrid.io:9876',
            'p2p.telosunlimited.io:9876',
            'seed-telos.infinitybloc.io:9877',
            'p2p.telos.eosdetroit.io:1337',
            'a.tlos.goodblock.io:9876',
            'p2p.telosvoyager.io:9876',
            'p2p.telosuk.io:9876',
            'seed1.telos.eosindex.io:9876',
            'telosafrique.eosnairobi.io:9476',
            'p2p.theteloscope.io:9876',
            'api.eosimpera:9876',
            'p2p.telos.dutcheos.io:9876',
            'p2p.telos.africa:9876',
            'p2p.telos.cryptosuvi.io:2222',
            'telos.eosvibes.io:9876',
            'telos.eosphere.io:9876',
            'peer.telos.alohaeos.com:9876',
            'telos.eu.eosamsterdam.net:9120',
            'telosseed1.atticlab.net:9876',
            'telos.greymass.com:19871',
            'node2.us-west.telosglobal.io:9876',
            'node1.us-west.telosglobal.io:9876',
            'api.telos.kitchen:9876',
            'mainnet.telosusa.io:9877',
            '192.168.50.185:9876',
            '192.168.50.136:9876',
            '192.168.50.60:9876',
            '192.168.50.178:9876'
        ]
    }
}

hyperion = {
    'tag': 'telos.net/hyperion:0.1.0',
    'docker_path': 'hyperion',
    'chain': {
        'name': 'telos-mainnet',
        'long_name': 'Telos Mainnet',
        'chain_hash': '4667b205c6838ef70ff7988f6e8257e8be0e1284a2f59699054a018f743b1d11',
        'chain_id': 41,
        'http': 'http://localhost:8888',
        'ship': 'ws://localhost:29999',
        'router_host': '0.0.0.0',
        'router_port': 7000,

        'explorer': {
            'enabled': True,
            'chain_logo_url': 'http://raw.githubusercontent.com/telosnetwork/images/master/chain_icons/telos-logo-light.png',
            'server_name': '0.0.0.0:7000'
        },

        'telos-evm': {
            'enabled': True,
            'signer_account': 'rpc.evm',
            'signer_permission': 'active',
            'signer_key': '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',
            'contracts': {
                'main': 'eosio.evm' 
            },
            'debug': False,
            'indexerWebsocketHost': '0.0.0.0',
            'indexerWebsocketPort': '7300',
            'indexerWebsocketUri': 'ws://0.0.0.0:7300',
            'rpcWebsocketHost': '0.0.0.0',
            'rpcWebsocketPort': '7400'
        }
    },
    'indexer': {
        'name': 'hyperion-indexer',
        'log_volume': 'indexer_logs',
        'start_on': 180635436,
        'end_on': 0,
        'auto_stop': 0,
        'blacklists': {
            'actions': [],
            'deltas': []
        },
        'whitelists': {
            'actions': [
                'eosio.evm::call',
                'eosio.evm::create',
                'eosio.evm::doresources',
                'eosio.evm::init',
                'eosio.evm::openwallet',
                'eosio.evm::raw',
                'eosio.evm::receipt',
                'eosio.evm::setresources',
                'eosio.evm::withdraw'
            ],
            'deltas': [
                'eosio::global'
            ],
            'max_depth': 10,
            'root_only': False
        }
    },
    'api': {
        'name': 'hyperion-api',
        'log_volume': 'api_logs',
        'server_addr': '0.0.0.0',
        'server_port': 7000,
        'server_name': '0.0.0.0:7000',
        'provider_name': 'TelosEVM Mainnet node',
        'provider_url': 'https://telos.net'
    }
}

beats = {
    'name': 'beats',
    'tag': 'tevm:beats',
    'docker_path': 'beats'
}

default_config = {
    'redis': redis,
    'rabbitmq': rabbitmq,
    'elasticsearch': elasticsearch,
    'kibana': kibana,
    'nodeos': nodeos,
    'hyperion': hyperion,
    'beats': beats
}
