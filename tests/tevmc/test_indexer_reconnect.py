#!/usr/bin/env python3

import time


def test_indexer_reconnect(tevmc_local):
    tevmc = tevmc_local

    for msg in tevmc.stream_logs('telosevm-translator'):
        if 'drained' in msg:
            break

    tevmc.cleos.stop_nodeos(
        from_file=tevmc.config['nodeos']['log_path'])
    tevmc.is_nodeos_relaunch = True

    time.sleep(4)
    config = tevmc.config['nodeos']
    nodeos_params = {
        'data_dir': config['data_dir_guest'],
        'logfile': config['log_path'],
        'logging_cfg': '/root/logging.json'
    }
    output = tevmc.cleos.start_nodeos_from_config(
        '/root/config.ini',
        state_plugin=True,
        is_local=tevmc.is_local,
        **nodeos_params
    )

    for msg in tevmc.stream_logs('telosevm-translator'):
        if 'drained' in msg:
            break
