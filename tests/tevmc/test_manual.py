import pytest


@pytest.mark.randomize(False)
def test_manual_full(tevmc_local):
    tevmc = tevmc_local
    breakpoint()


@pytest.mark.randomize(False)
@pytest.mark.services('elastic', 'nodeos')
def test_manual_translator_dev(tevmc_mainnet):
    tevmc = tevmc_mainnet
    breakpoint()


@pytest.mark.randomize(False)
@pytest.mark.services(
    'redis', 'elastic', 'nodeos', 'indexer')
def test_manual_rpc_dev(tevmc_local):
    tevmc = tevmc_local
    breakpoint()
