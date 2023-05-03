#!/usr/bin/env python3

redis = {
    'name': 'redis',
    'docker_path': 'redis',
    'tag': 'tevm:redis',
    'host': '127.0.0.1',
    'port': 6379,
    'conf_dir': 'config',
    'data_dir': 'data'
}

rabbitmq = {
    'name': 'rabbitmq',
    'docker_path': 'rabbitmq',
    'tag': ':rabbitmq',
    'host': '127.0.0.1:5672',
    'api': '127.0.0.1:15672',
    'node_name': 'rabbit@localhost',
    'dist_port': 25672,
    'prometheus_port': 15692,
    'user': 'username',
    'pass': 'password',
    'vhost': '/hyperion',
    'conf_dir': 'config',
    'data_dir': 'data'
}

elasticsearch = {
    'name': 'elasticsearch',
    'docker_path': 'elasticsearch',
    'tag': 'tevm:elasticsearch',
    'protocol':  'http',
    'host': '127.0.0.1:9200',
    'ingest_nodes': ['127.0.0.1:9200'],
    'elastic_pass': 'password',
    'user': 'hyper',
    'pass': 'password',
    'data_dir': 'data',
    'logs_dir': 'logs'
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
    'tag': 'tevm:nodeos-3.1.0-evm',
    'docker_path': 'eosio',
    'data_dir_guest': '/mnt/dev/data',
    'data_dir_host': 'data',
    'conf_dir': 'config',
    'contracts_dir': 'contracts',
    'genesis': 'testnet',
    'snapshot': '/snapshot-testnet-20211020-blknum-136229794.bin',
    'log_path': '/root/nodeos.log',
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
        
        'sig_provider': 'EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L=KEY:5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',    

        'disable_subjective_billing': True,
        'max_transaction_time': 500,

        'plugins': [
            'eosio::http_plugin',
            'eosio::chain_api_plugin',
            'eosio::state_history_plugin'
        ],
        'peers': [
            'testnet2.telos.eosusa.news:59877',
            '109.237.25.217:3876',
            'testnet.telos.caleos.io:9879',
            'testnet.telos.eossweden.eu:8022',
            '178.200.204.188:9876',
            'p2p.testnet.telosgreen.com:9876',
            'telostestnet.ikuwara.com:9876',
            'testnet.eos.miami:13975',
            'testnet-p2p.telosuk.io:9876',
            '52.175.200.62:9876',
            'test.p2p.telosvoyager.io:2876',
            'testnet.theteloscope.io:19876'
        ]
    }
}

hyperion = {
    'tag': 'tevm:hyperion',
    'docker_path': 'hyperion',
    'conf_dir': 'config',
    'logs_dir': 'logs',
    'chain': {
        'name': 'telos-testnet',
        'long_name': 'Telos Testnet',
        'chain_hash': '1eaa0824707c8c16bd25145493bf062aecddfeb56c736f6ba6397f3195f33c9f', 
        'chain_id': 41,
        'http': 'http://127.0.0.1:8888',
        'ship': 'ws://127.0.0.1:29999',
        'router_host': '127.0.0.1',
        'router_port': 7120,

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
            'debug': True,
            'nodeos_read': 'http://127.0.0.1:8888',
            'indexerWebsocketHost': '0.0.0.0',
            'indexerWebsocketPort': '7300',
            'indexerWebsocketUri': 'ws://127.0.0.1:7300/evm',
            'rpcWebsocketHost': '0.0.0.0',
            'rpcWebsocketPort': '7400'
        }
    },
    'indexer': {
        'name': 'hyperion-indexer',
        'start_on': 136229794,
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
        'server_addr': '0.0.0.0',
        'server_port': 7000,
        'server_name': 'rpcX.XX.telos.net',
        'provider_name': 'TelosEVM testnet',
        'provider_url': 'https://telos.net'
    }
}

beats = {
    'name': 'beats',
    'tag': 'tevm:beats',
    'docker_path': 'beats',
    'conf_dir': 'config',
    'data_dir': 'data'
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
