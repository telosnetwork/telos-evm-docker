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
    'genesis': 'local',
    'v2_api': 'disabled',
    'nodeos_bin': 'nodeos',
    'eosio.evm': 'eosio.evm/receiptless',
    'chain_id': 'override',
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
        'allowed_connection': 'any',
        'http_max_response_time': 100000,
        'http_max_body_size': 100000000,

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
        'peers': [],
        'subst': {
            'eosio.evm': '/opt/eosio/bin/contracts/eosio.evm/regular/regular.wasm'
        }
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
    'start_block': 2,
    'evm_block_delta': 0,
    'evm_validate_hash': '',
    'stop_block': -1,
    'prev_hash': '',
    'worker_amount': 1,
    'elastic_dump_size': 1,
    'elastic_timeout': 1000 * 20
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
    'remote_endpoint': 'http://127.0.0.1:7000/evm',
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
    'elastic_prefix': 'telos-local-tevmc',
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

