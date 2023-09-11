#!/usr/bin/env python3

import logging
from elasticsearch import Elasticsearch

import pytest

from tevmc.cmdline.repair import perform_data_repair
from tevmc.config import load_config


EVM_1_5_ENDPOINT = 'https://mainnet15a.telos.net/evm'

@pytest.mark.randomize(False)
@pytest.mark.tevmc_params(is_producer=False)
@pytest.mark.services('redis', 'elastic', 'nodeos', 'indexer', 'rpc')
def test_repair_dirty_db(tevmc_mainnet):
    tevmc = tevmc_mainnet

    tevmc.cleos.wait_blocks(120_000)

    # ungracefull nodeos stop
    tevmc.containers['nodeos'].stop()

    # assert db is dirty
    tevmc.is_nodeos_relaunch = True
    tevmc.start_nodeos(do_init=False)
    is_dirty = False
    for line in tevmc._stream_logs_from_main_dir('nodeos', lines=10):
        logging.info(line)
        if 'database dirty flag set (likely due to unclean shutdown)' in line:
            is_dirty = True
            break

    assert is_dirty

    # delete single elastic block creating gap
    latest_block = tevmc.cleos.eth_get_block_by_number('latest')['result']
    es_config = tevmc.config['elasticsearch']
    es = Elasticsearch(f'{es_config["protocol"]}://{es_config["host"]}')

    delete_block_num = int(latest_block['number'], 16) - 10

    query = {
        'query': {
            'term': {
                'block_num': delete_block_num
            }
        }
    }
    logging.info(f'deleting block num {delete_block_num}')
    elastic_prefix = tevmc.config['telos-evm-rpc']['elastic_prefix']
    es.delete_by_query(index=f'{elastic_prefix}-delta-*', body=query)

    # tear down node
    tevmc.stop()

    # run repair
    perform_data_repair(
        tevmc.root_pwd / 'tevmc.json', progress=False)

    # update config
    tevmc.is_nodeos_relaunch = False
    tevmc.config = load_config(tevmc.root_pwd, 'tevmc.json')

    # pull up node
    tevmc.start()
    tevmc.cleos.wait_blocks(10_000)

    # get latest evm block
    block = tevmc.cleos.eth_get_block_by_number('latest')['result']

    # query remote for same block
    remote_block = tevmc.cleos.eth_get_block_by_number(
        block['number'], url=EVM_1_5_ENDPOINT)['result']

    # check hashes match
    assert block['hash'] == remote_block['hash']
