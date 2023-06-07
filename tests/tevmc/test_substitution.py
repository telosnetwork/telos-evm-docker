#!/usr/bin/env python3

import time
import logging

from elasticsearch import Elasticsearch


def test_subst_after_contract_redeploy(testnet_from_228038712):

    tevmc = testnet_from_228038712
    delta_index = tevmc.config['telos-evm-rpc']['elastic_prefix'] + '-delta-*'
    action_index = tevmc.config['telos-evm-rpc']['elastic_prefix'] + '-action-*'

    es_config = tevmc.config['elasticsearch']
    es = Elasticsearch(
        f'{es_config["protocol"]}://{es_config["host"]}',
        basic_auth=(
            es_config['user'], es_config['pass']
        )
    )

    tevmc.cleos.wait_blocks(350000)

    for msg in tevmc.stream_logs(tevmc.containers['telosevm-translator']):
        tevmc.logger.info(msg.rstrip())
        if 'drained' in msg:
            break

    def get_last_indexed_tx():
        result = es.search(
            index=action_index,
            size=1,
            sort={'@raw.block': 'desc'},
            query={
                'query_string': {
                    'query': '@raw.itxs: *'
                }
            }
        )
        return result['hits']['hits'][0]['_source']['@raw']

    def get_last_indexed_block():
        result = es.search(
            index=delta_index,
            size=1,
            sort={'@global.block_num': 'desc'},
            query={
                'match_all': {}
            }
        )
        return result['hits']['hits'][0]['_source']

    last_block = get_last_indexed_block()
    while last_block['block_num'] < 228399099:
        logging.info(f'last indexed: {last_block}')
        time.sleep(5)
        last_block = get_last_indexed_block()

    last_tx = get_last_indexed_tx()
    assert last_tx['block'] > 228399099
