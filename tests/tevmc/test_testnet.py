#!/usr/bin/env python3


def test_bootstrap(tevmc_testnet_no_wait):
    ...


def test_restart(tevmc_testnet_no_wait):
    tevmc = tevmc_testnet_no_wait

    tevmc.stop()

    assert (tevmc.docker_wd /
        'leap/data/blocks/blocks.log').is_file()

    tevmc.start()

def test_start_from_latest(tevmc_testnet_latest):
    tevmc = tevmc_testnet_latest

    breakpoint()
