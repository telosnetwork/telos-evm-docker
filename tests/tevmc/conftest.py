#!/usr/bin/env python3

from tevmc.testing.fixtures.local import tevm_node as tevmc_local
from tevmc.testing.fixtures.local import tevm_node_non_random as tevmc_local_non_rand
from tevmc.testing.fixtures.local import nodeos as nodeos_local

from tevmc.testing.fixtures.testnet import tevm_node as tevmc_testnet
from tevmc.testing.fixtures.testnet import tevm_node_latest as tevmc_testnet_latest
from tevmc.testing.fixtures.testnet import tevm_node_no_wait as tevmc_testnet_no_wait
from tevmc.testing.fixtures.testnet import nodeos_latest as nodeos_testnet_latest

from tevmc.testing.fixtures.mainnet import tevm_node as tevmc_mainnet
from tevmc.testing.fixtures.mainnet import tevm_node_latest as tevmc_mainnet_latest
from tevmc.testing.fixtures.mainnet import tevm_node_no_wait as tevmc_mainnet_no_wait

