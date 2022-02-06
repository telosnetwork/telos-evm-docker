#!/usr/bin/env python3


def test_bootstrap(tevmc_testnet_no_wait):
    ...


def test_restart(tevmc_testnet_no_wait):
    tevmc_testnet_no_wait.stop()

    assert (
        tevmc_testnet_no_wait.docker_wd /
            'eosio/data/blocks/blocks.log').is_file() 

    tevmc_testnet_no_wait.start()
