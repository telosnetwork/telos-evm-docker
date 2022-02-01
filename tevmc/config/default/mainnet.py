#!/usr/bin/env python3

redis = {
    'name': 'redis',
    'docker_path': 'redis',
    'tag': 'tevm:redis',
    'host': 'localhost',
    'port': 6379,
    'data_volume': 'redis_data'
}

rabbitmq = {
    'name': 'rabbitmq',
    'docker_path': 'rabbitmq',
    'tag': 'tevm:rabbitmq',
    'host': 'localhost:5672',
    'api': 'localhost:15672',
    'user': 'username',
    'pass': 'password',
    'vhost': '/hyperion',
    'data_volume': 'rabbitmq_data'
}

elasticsearch = {
    'name': 'elasticsearch',
    'docker_path': 'elasticsearch',
    'tag': 'tevm:elasticsearch',
    'protocol':  'http',
    'host': 'localhost:9200',
    'ingest_nodes': ['localhost:9200'],
    'user': 'elastic',
    'pass': 'password',
    'data_volume': 'elasticsearch_data'
}

kibana = {
    'name': 'kibana',
    'docker_path': 'kibana',
    'tag': 'tevm:kibana',
    'host': '0.0.0.0',
    'port': 5601
}

nodeos = {
    'name': 'nodeos',
    'tag': 'tevm:nodeos-2.1.0-evm',
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
            'telos.eu.eosamsterdam.net:9120',
            'p2p.telos.eosargentina.io:9879',
            'p2p.telos.eosdetroit.io:1337',
            'peer2-telos.eosphere.io:9876',
            'p2p.telos.africa:9877',
            'telos.eossweden.eu:8012',
            'p2p.telosuk.io:9876',
            'seed.telosmadrid.io:9876',
            'seed.teloskorea.com:9876',
            'p2p2.telos.telosgreen.com:9877'
        ]
    }
}

hyperion = {
    'tag': 'tevm:hyperion',
    'docker_path': 'hyperion',
    'chain': {
        'name': 'telos-mainnet',
        'long_name': 'Telos Mainnet',
        'chain_hash': '4667b205c6838ef70ff7988f6e8257e8be0e1284a2f59699054a018f743b1d11',
        'chain_id': 40,
        'http': 'http://localhost:8888',
        'ship': 'ws://localhost:29999',
        'router_host': '0.0.0.0',
        'router_port': 7000,

        'explorer': {
            'enabled': True,
            'chain_logo_url': 'http://raw.githubusercontent.com/telosnetwork/images/master/chain_icons/telos-logo-light.png',
            'server_name': 'rpcX.XX.telos.net'
        },

        'telos-evm': {
            'enabled': True,
            'signer_account': 'rpc.evm',
            'signer_permission': 'rpc',
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
        'rewrite': False,
        'live_reader': True,
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
        'server_name': 'rpcX.XX.telos.net',
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
