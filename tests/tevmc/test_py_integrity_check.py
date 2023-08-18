#!/usr/bin/env python3

from hashlib import sha256

from datetime import datetime, timedelta

import pytest

from elasticsearch import Elasticsearch

from tevmc.testing.database import ElasticDataIntegrityError, ElasticDriver


def get_suffix(block_num: int, docs_per_index: int):
    return str(int(block_num / float(docs_per_index))).zfill(8)


def prepare_db_for_test(
    tevmc,
    start_time,
    ranges,
    txs=[],
    action_index_spec='action-v1.5',
    delta_index_spec='delta-v1.5',
    docs_per_index=10_000_000
):
    rpc_conf = tevmc.config['telos-evm-rpc']
    es_config = tevmc.config['elasticsearch']
    es = Elasticsearch(
        f'{es_config["protocol"]}://{es_config["host"]}',
        basic_auth=(
            es_config['user'], es_config['pass']
        )
    )
    es.indices.delete(
        index=f'{rpc_conf["elastic_prefix"]}-{action_index_spec}-*'
    )
    es.indices.delete(
        index=f'{rpc_conf["elastic_prefix"]}-{delta_index_spec}-*',
    )

    ops = []
    for rstart, rend in ranges:
        for i in range(rstart, rend + 1, 1):
            delta_index = f'{rpc_conf["elastic_prefix"]}-{delta_index_spec}-{get_suffix(i, docs_per_index)}'
            ops.append({
                "index": {
                    "_index": delta_index
                }
            })
            ops.append({
                "@timestamp": start_time + (i * timedelta(seconds=0.5)),
                "@global": {
                    "block_num": i
                },
                "block_num": i - 10
            })

    indices = []
    for tx in txs:
        action_index = f'{rpc_conf["elastic_prefix"]}-{action_index_spec}-{get_suffix(tx["@raw.block"], docs_per_index)}'
        indices.append(action_index)
        ops.append({
            "index": {
                "_index": action_index
            }
        })
        ops.append(tx)

    for idx in indices:
        es.indices.create(
            index=idx,
            ignore=400,
            body={
                'mappings': {
                    'properties': {
                        '@raw.hash': {
                            'type': 'keyword'
                        }
                    }
                }
            }
        )


    es.bulk(operations=ops, refresh=True)


@pytest.mark.randomize(False)
@pytest.mark.services('elastic', 'kibana')
def test_python_elastic_integrity_tool(tevmc_local):
    tevmc = tevmc_local
    elastic = ElasticDriver(tevmc.config)

    # no gaps
    prepare_db_for_test(
        tevmc, datetime.now(), [(100, 200)])

    elastic.full_integrity_check()

    # gap in delta docs
    prepare_db_for_test(
        tevmc, datetime.now(), [(100, 120), (122, 200)])

    with pytest.raises(ElasticDataIntegrityError) as error:
        elastic.full_integrity_check()

    assert 'Gap found! 121' in str(error)

    # duplicate block range
    prepare_db_for_test(
        tevmc, datetime.now(), [(100, 200), (150, 151)])

    with pytest.raises(ElasticDataIntegrityError) as error:
        elastic.full_integrity_check()

    assert 'Duplicates found!' in str(error)

    # duplicate by hash
    test_hash = sha256(b'test_tx').hexdigest()
    txs = [
        {'@raw.block': 110, '@raw.hash': test_hash},
        {'@raw.block': 115, '@raw.hash': test_hash}
    ]
    prepare_db_for_test(
        tevmc, datetime.now(), [(100, 200)], txs=txs)

    with pytest.raises(ElasticDataIntegrityError) as error:
        elastic.full_integrity_check()

    assert 'Duplicates found!' in str(error)
