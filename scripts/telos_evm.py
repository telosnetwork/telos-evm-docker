#!/usr/bin/env python3

import json
import time
import shutil
import logging

from typing import List, Dict
from pathlib import Path
from contextlib import contextmanager, ExitStack

import docker
import requests

from docker.types import LogConfig, Mount
from py_eosio.cleos import CLEOS
from py_eosio.sugar import (
    wait_for_attr, get_container,
    docker_open_process, docker_wait_process
)


DEFAULT_NETWORK_NAME = 'docker_hyperion'
DEFAULT_VOLUME_NAME = 'eosio_volume'


class TEVMController:

    def __init__(
        self,
        producer_key: str = '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL'
    ):
        self.client = docker.from_env()
        self.root_pwd = Path(__file__).parent.parent.resolve()
        self.exit_stack = ExitStack()
        self.producer_key = producer_key

        self.network = None

        self._redis_container = None
        self._rabbitmq_container = None
        self._elasticsearch_container = None
        self._kibana_container = None
        self._eosio_node_container = None
        self._hyperion_indexer_container = None
        self._hyperion_api_container = None

    def init_network(self):
        """Try to attach to already created default network or create.
        """

        try:
            self.network = self.client.networks.get(DEFAULT_NETWORK_NAME)
        except docker.errors.NotFound:
            self.network = self.client.networks.create(DEFAULT_NETWORK_NAME, driver='bridge')

    @contextmanager
    def temporary_directory(self, dir: Path):
        """Manages a temporary directory, creates it, gives permissions then
        yields the directory, on control return deletes it ignoring errors.
        """

        shutil.rmtree(dir, ignore_errors=True)
        dir.mkdir(parents=True)
        logging.info(f'created temp dir: {dir}')
        dir.chmod(0o777)

        yield dir
        shutil.rmtree(dir, ignore_errors=True)
        logging.info(f'deleted temp dir: {dir}')

    @contextmanager
    def open_container(
        self, 
        name: str, image: str,
        force_unique: bool = False,
        *args, **kwargs
    ):
        """Attaches to a running docker container, or in its absence starts a new one,
        use ``force_unique`` to always start a new container.
        
        Also waits for container to get ip address.
        """
        try:
            logging.info(f'opening container {name}')
            container = get_container(
                self.client,
                image,
                force_unique=force_unique,
                *args, **kwargs,
                name=name,
                detach=True,
                network=self.network.id,
                log_config=LogConfig(
                    type=LogConfig.types.JSON,
                    config={'max-size': '2m' }),
                restart_policy={
                    "Name": "on-failure", "MaximumRetryCount": 3})

            logging.info(f'waiting on networking check')
            ip = wait_for_attr(container, (
                'NetworkSettings', 'Networks', self.network.name, 'IPAddress'))
            logging.info(f'container at {ip} started')

            yield container

        finally:
            logging.info(f'stopping container \"{name}\"')
            try:
                container.stop()
            except docker.errors.APIError:
                pass

            logging.info(f'remove image for \"{name}\"')
            try:
                container.remove()

            except docker.errors.APIError:
                pass

    def start_redis(self, port: str = '6379/tcp'):
        """Start redis container and await port init.
        """
        self._redis_container = self.exit_stack.enter_context(
            self.open_container(
                'redis',
                'redis:5.0.9-buster',
                ports={port: port}
            )
        )

        self._redis_port = wait_for_attr(
            self._redis_container,
            ('NetworkSettings', 'Ports', port)
        )

    def start_rabbitmq(
        self,
        ports: Dict[str, str] = {
            '5672/tcp': '5672/tcp',
            '15672/tcp': '15672/tcp'
        }
    ):
        """Create temporary rabbitmq data dir, start container and wait for ports init.
        """
        self._rabbitmq_dir = self.exit_stack.enter_context(
            self.temporary_directory(self.root_pwd / 'docker/rabbitmq/data'))

        mounts = [
            Mount(
                '/var/lib/rabbitmq',  # target
                str(self._rabbitmq_dir),  # source
                'bind'
            )
        ]
        self._rabbitmq_container = self.exit_stack.enter_context(
            self.open_container(
                'rabbitmq',
                'rabbitmq:3.8.3-management',
                environment={
                    'RABBITMQ_DEFAULT_USER': 'username',
                    'RABBITMQ_DEFAULT_PASS': 'password',
                    'RABBITMQ_DEFAULT_VHOST': '/hyperion',
                },
                ports=ports,
                mounts=mounts
            )
        )

        self._rabbitmq_port = wait_for_attr(
            self._rabbitmq_container,
            ('NetworkSettings', 'Ports', ports['5672/tcp'])
        )

        self._rabbitmq_port = wait_for_attr(
            self._rabbitmq_container,
            ('NetworkSettings', 'Ports', ports['15672/tcp'])
        )

    def start_elasticsearch(self, port: str = '9200/tcp'):
        """Create temporary elasticsearch data dir, start container and wait
        for ports init.

        Then consume logs until boostrap.
        """
        self._elasticsearch_dir = self.exit_stack.enter_context(
            self.temporary_directory(self.root_pwd / 'docker/elasticsearch/data'))

        mounts = [
            Mount(
                '/usr/share/elasticsearch/data',  # target
                str(self._elasticsearch_dir),  # source
                'bind'
            )
        ]

        self._elasticsearch_container = self.exit_stack.enter_context(
            self.open_container(
                'elasticsearch',
                'docker.elastic.co/elasticsearch/elasticsearch:7.7.1',
                environment={
                    'discovery.type': 'single-node',
                    'cluster.name': 'es-cluster',
                    'node.name': 'es01',
                    'bootstrap.memory_lock': 'true',
                    'xpack.security.enabled': 'false',  # TODO: Turn security ON
                    'ES_JAVA_OPTS': '-Xms2g -Xmx2g',
                    'ES_NETWORK_HOST': '0.0.0.0',
                    'ELASTIC_USERNAME': 'elastic',
                    'ELASTIC_PASSWORD': 'password'
                },
                ports={port: port},
                mounts=mounts
            )
        )

        self._elasticsearch_port = wait_for_attr(
            self._elasticsearch_container,
            ('NetworkSettings', 'Ports', port)
        )

        for chunk in self._elasticsearch_container.logs(stream=True):
            msg = chunk.decode('utf-8')
            if 'recovered [0] indices into cluster' in msg:
                break

    def start_kibana(self, port: str = '5601/tcp'):
        """Start kibana container and await port init.
        """
        self._kibana_container = self.exit_stack.enter_context(
            self.open_container(
                'kibana',
                'docker.elastic.co/kibana/kibana:7.7.1',
                environment={
                    'ELASTICSEARCH_HOSTS': 'http://elasticsearch:9200',
                    'ELASTICSEARCH_USERNAME': 'elastic',
                    'ELASTICSEARCH_PASSWORD': 'password'
                },
                ports={port: port}
            )
        )

        self._kibana_port = wait_for_attr(
            self._kibana_container,
            ('NetworkSettings', 'Ports', port)
        )

    def start_eosio_node(
        self,
        ports: Dict[str, str] = {
            '8080/tcp': '8080/tcp',
            '8888/tcp': '8888/tcp'
        }
    ):
        """Get eosio_volume or create, start eosio_nodeos container and wait
        for ports init.

        - Initialize CLEOS wrapper and setup keosd & wallet.
        - Launch nodeos with config.ini
        - Wait for nodeos to produce blocks
        - Create evm accounts and deploy contract
        """

        # search for volume and delete if exists, then create
        try:
            vol = self.client.volumes.get(DEFAULT_VOLUME_NAME)
            vol.remove()

        except docker.errors.NotFound:
            vol = self.client.volumes.create(
                name=DEFAULT_VOLUME_NAME)

        self._eosio_node_volume = vol

        # open container
        self._eosio_node_container = self.exit_stack.enter_context(
            self.open_container(
                'eosio_nodeos',
                'eosio:2.0.13-evm',
                command=['/bin/bash', '-c', 'trap : TERM INT; sleep infinity & wait'],
                ports=ports,
                volumes=[
                    f'{self._eosio_node_volume.name}:/mnt/dev/data'
                ]
            )
        )

        # network check
        self._eosio_node_port = wait_for_attr(
            self._eosio_node_container,
            ('NetworkSettings', 'Ports', ports['8080/tcp'])
        )
        self._eosio_node_port = wait_for_attr(
            self._eosio_node_container,
            ('NetworkSettings', 'Ports', ports['8888/tcp'])
        )

        # setup cleos wrapper
        cleos = CLEOS(
            self.client,
            self._eosio_node_container)

        # init wallet
        cleos.start_keosd() 
        cleos.setup_wallet(self.producer_key)

        # init nodeos
        cleos.start_nodeos_from_config(
            '/root',
            state_plugin=True,
            genesis='/root/genesis.json')

        # await for nodeos to produce a block
        cleos.wait_produced()
        cleos.boot_sequence()

        # create evm accounts and deploy contract
        cleos.create_account_staked('eosio', 'eosio.evm', ram=1024000)
        cleos.create_account_staked('eosio', 'fees.evm', ram=1024000)
        cleos.create_account_staked('eosio', 'rpc.evm', ram=1024000)

        cleos.deploy_contract(
            'eosio.evm',
            '/usr/opt/telos.contracts/contracts/eosio.evm',
            privileged=True,
            create_account=False
        )

        self.cleos = cleos

    def start_hyperion_indexer(self):
        """Start hyperion_indexer container and await port init.
        """
        self._hyperion_indexer_container = self.exit_stack.enter_context(
            self.open_container(
                'hyperion-indexer',
                'telos.net/hyperion:0.1.0',
                command=[
                    '/bin/bash', '-c',
                    '/home/hyperion/scripts/run-hyperion.sh telos-testnet-indexer'
                ],
                force_unique=True
            )
        )

    def start_hyperion_api(self, port: str = '7000/tcp'):
        """Start hyperion_api container and await port init.
        """
        self._hyperion_api_container = self.exit_stack.enter_context(
            self.open_container(
                'hyperion-api',
                'telos.net/hyperion:0.1.0',
                command=[
                    '/bin/bash', '-c',
                    '/home/hyperion/scripts/run-hyperion.sh telos-testnet-api'
                ],
                force_unique=True,
                ports={port: port}
            )
        )

        self._hyperion_api_port = wait_for_attr(
            self._hyperion_api_container,
            ('NetworkSettings', 'Ports', port)
        )

        for chunk in self._hyperion_api_container.logs(stream=True):
            msg = chunk.decode('utf-8')
            logging.info(msg.rstrip())
            if 'api ready' in msg:
                break

        
    def __enter__(self):
        self.init_network()

        self.start_eosio_node()
        self.start_redis()
        self.start_rabbitmq()
        self.start_elasticsearch()
        self.start_kibana()

        self.start_hyperion_indexer()
        self.start_hyperion_api()

        return self

    def __exit__(self, type, value, traceback):
        self.exit_stack.pop_all().close()
        self.network.remove()



if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument( '-l',
                        '--loglevel',
                        default='warning',
                        help='Provide logging level. Example --loglevel debug, default=warning' )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.loglevel.upper(),
        format='%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%H:%M'
    )

    with TEVMController() as tevm:
        logging.info('control point reached')
        try:
            for i in range(120):
                try:
                    resp = requests.get(
                        'http://127.0.0.1:7000/v2/history/get_actions',
                        params={
                            'account': 'eosio.evm'
                        }
                    ).json()
                except requests.exceptions.ConnectionError:
                    pass

                if len(resp['actions']) > 0:
                    logging.info(resp)
                    logging.critical("\n\n\nINDEXED\n\n\n")
                    break

                time.sleep(1)

        except KeyboardInterrupt:
            ...
