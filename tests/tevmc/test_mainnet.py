#!/usr/bin/env python3


def test_bootstrap(tevmc_mainnet_no_wait):
    ...


def test_restart(tevmc_mainnet_no_wait):
    tevmc = tevmc_mainnet_no_wait

    tevmc.stop()
    tevmc.is_relaunch = True

    assert (tevmc.docker_wd /
        'eosio/data/blocks/blocks.log').is_file() 

    tevmc.start()