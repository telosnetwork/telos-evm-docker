#!/usr/bin/env python3

import sys
import json


import click



from .cli import cli


@cli.command()
@click.option(
    '--hyperion-cfg-path', default='docker/hyperion/config/chains/telos-testnet.config.json',
    help='Path to hyperion config file')
@click.option(
    '--indexer-start-on', default=1,
    help='Block number at which hyperion indexer must start.')
@click.option(
    '--indexer-stop-on', default=0,
    help='Block number at which hyperion indexer must stop.')
@click.option(
    '--evm-abi-path', default='docker/eosio/contracts/eosio.evm/eosio.evm.abi',
    help='Path to eosio.evm abi file, to parse actions and support --index-only-evm')
@click.option(
    '--index-only-evm/--index-all', default=False,
    help='Show output while waiting for bootstrap.')
def config(
    hyperion_cfg_path,
    indexer_start_on,
    indexer_stop_on,
    evm_abi_path,
    index_only_evm
):

    def decode_or_die(file):
        try:
            return json.loads(file.read())

        except json.decoder.JSONDecodeError as e:
            print('error parsing config! {e}')
            sys.exit(1)

    # hyperion
    with open(hyperion_cfg_path) as config_file:
        config = decode_or_die(config_file)

    chain_name = config['settings']['chain']

    # index_only_evm
    # hyperion has an indexer action whitelist, so to only index
    # evm transaction we must add all eosio.evm actions to the 
    # whitelist, to dynamically get all the actions we parse the
    # provided abi file
    deltas = []
    actions = []
    if index_only_evm:
        with open(evm_abi_path, 'r') as abi_file:
            abi = decode_or_die(abi_file)

        deltas = [f'{chain_name}::eosio::global']
        actions = [
            f'{chain_name}::eosio.evm::{row["name"]}' for row in abi['actions']
        ]

    config['whitelists']['actions'] = actions
    config['whitelists']['deltas'] = deltas

    config['indexer']['start_on'] = indexer_start_on
    config['indexer']['stop_on'] = indexer_stop_on

    # truncate config and re-write
    with open(hyperion_cfg_path, 'w+') as config_file:
        config_file.write(json.dumps(config, indent=4))
