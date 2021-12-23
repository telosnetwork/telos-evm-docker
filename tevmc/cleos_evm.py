#!/usr/bin/env python3

import time
import requests

from py_eosio.cleos import CLEOS


class CLEOSEVM(CLEOS):

    def __init__(
        self,
        *args, 
        hyperion_api_endpoint: str = 'http://127.0.0.1:7000',
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        self.hyperion_api_endpoint = hyperion_api_endpoint


    """    eosio.evm interaction
    """
    def create_evm_account(
        self,
        account: str,
        salt: str
    ):
        return self.push_action(
            'eosio.evm',
            'create',
            [account, salt],
            f'{account}@active'
        )

    """    hyperion interaction
    """
    def hyperion_health(self) -> int:
        return requests.get(
            f'{self.hyperion_api_endpoint}/v2/health').json()

    def hyperion_await_evm_tx(self, tx_hash):
        while True:
            resp = requests.get(
                f'{self.hyperion_api_endpoint}/v2/evm/get_transactions',
                params={'hash': tx_hash}).json()

            breakpoint()

    def hyperion_await_tx(self, tx_id):
        while True:
            resp = requests.get(
                f'{self.hyperion_api_endpoint}/v2/history/get_transaction',
                params={'id': tx_id}).json()

            if 'executed' not in resp:
                logging.warning(resp)

            if resp['executed']:
                break

            self.logger.info('await transaction:')
            self.logger.info(resp)
            time.sleep(0.1)

    def hyperion_get_actions(self, **kwargs):
        return requests.get(
            f'{self.hyperion_api_endpoint}/v2/history/get_actions',
            params=kwargs
        ).json()

        
