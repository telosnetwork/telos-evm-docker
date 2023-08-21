#!/usr/bin/env python3

from hashlib import sha256

from datetime import datetime

import pytest

from tevmc.testing.database import ElasticDriver, ElasticDataIntegrityError

from conftest import prepare_db_for_test


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

    # whole index gap
    prepare_db_for_test(
        tevmc, datetime.now(), [(1, 1), (20_000_000, 20_000_000)])

    with pytest.raises(ElasticDataIntegrityError) as error:
        elastic.full_integrity_check()

    assert 'Gap found! 2' in str(error)

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
