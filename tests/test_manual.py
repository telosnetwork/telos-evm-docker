import pytest


@pytest.mark.randomize(False)
@pytest.mark.services('nodeos')
def test_manual_nodeos(tevmc_local):
    tevmc = tevmc_local
    breakpoint()

@pytest.mark.randomize(False)
@pytest.mark.bootstrap(True)
@pytest.mark.services('nodeos')
def test_manual_nodeos_bootstrapped(tevmc_local):
    tevmc = tevmc_local
    breakpoint()


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


@pytest.mark.randomize(False)
@pytest.mark.services('elastic', 'nodeos', 'indexer')
def test_manual_wait(tevmc_mainnet):
    tevmc = tevmc_mainnet
    breakpoint()


@pytest.mark.randomize(False)
@pytest.mark.services('nodeos')
@pytest.mark.tevmc_params(from_latest=True, additional_nodeos_params=[
    # '--plugin', 'eosio::subst_plugin',
    '--override-max-tx-time',
    '--max-transaction-time', '499'
])
def test_manual_nodeos_latest_testnet_gpo_bypass(tevmc_testnet):
    tevmc = tevmc_testnet
    breakpoint()
