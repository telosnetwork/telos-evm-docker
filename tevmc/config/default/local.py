#!/usr/bin/env python3

redis = {
    'name': 'redis',
    'docker_path': 'redis',
    'tag': 'tevm:redis',
    'host': 'localhost',
    'port': 6379,
    'conf_dir': 'config',
    'data_dir': 'data'
}

rabbitmq = {
    'name': 'rabbitmq',
    'docker_path': 'rabbitmq',
    'tag': 'tevm:rabbitmq',
    'host': 'localhost:5672',
    'api': 'localhost:15672',
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
    'host': 'localhost:9200',
    'ingest_nodes': ['localhost:9200'],
    'user': 'elastic',
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
    'tag': 'tevm:nodeos-2.1.0-evm',
    'docker_path': 'eosio',
    'data_dir_guest': '/mnt/dev/data',
    'data_dir_host': 'data',
    'conf_dir': 'config',
    'contracts_dir': 'contracts',
    'genesis': 'local',
    'log_path': '/root/nodeos.log',
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

        'agent_name': 'Telos Local Testnet',


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

        'enable_stale_production': True,
        
        'sig_provider': 'EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L=KEY:5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',
    
        'disable_subjective_billing': True,
        'max_transaction_time': 500,

        'plugins': [
            'eosio::http_plugin',
            'eosio::chain_plugin',
            'eosio::chain_api_plugin',
            'eosio::net_plugin',
            'eosio::producer_plugin',
            'eosio::producer_api_plugin',
            'eosio::state_history_plugin'
        ],
        'peers': []
    }
}

hyperion = {
    'tag': 'tevm:hyperion',
    'docker_path': 'hyperion',
    'conf_dir': 'config',
    'logs_dir': 'logs',
    'chain': {
        'name': 'telos-local-testnet',
        'long_name': 'Telos Local Testnet',
        'chain_hash': '1eaa0824707c8c16bd25145493bf062aecddfeb56c736f6ba6397f3195f33c9f',
        'chain_id': 41,
        'http': 'http://localhost:8888',
        'ship': 'ws://localhost:29999',
        'router_host': 'localhost',
        'router_port': 7000,

        'explorer': {
            'enabled': True,
            'chain_logo_url': 'http://raw.githubusercontent.com/telosnetwork/images/master/chain_icons/telos-logo-light.png',
            'server_name': 'localhost:7000'
        },

        'telos-evm': {
            'enabled': True,
            'signer_account': 'rpc.evm',
            'signer_permission': 'active',
            'signer_key': '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',
            'contracts': {
                'main': 'eosio.evm' 
            },
            'debug': True,
            'indexerWebsocketHost': '0.0.0.0',
            'indexerWebsocketPort': '7300',
            'indexerWebsocketUri': 'ws://localhost:7300',
            'rpcWebsocketHost': '0.0.0.0',
            'rpcWebsocketPort': '7400'
        }
    },
    'indexer': {
        'name': 'hyperion-indexer',
        'start_on': 1,
        'end_on': 0,
        'rewrite': False,
        'live_reader': True,
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
        'server_addr': '0.0.0.0',
        'server_port': 7000,
        'server_name': '0.0.0.0:7000',
        'provider_name': 'TelosEVM local node development',
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
