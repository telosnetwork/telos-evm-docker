#!/usr/bin/env python3

import os
import sys
import time
import shutil
import logging

from typing import List, Dict, Optional
from pathlib import Path
from contextlib import contextmanager, ExitStack

import docker
import requests

from docker.types import LogConfig, Mount
from requests.auth import HTTPBasicAuth
from py_eosio.sugar import (
    Asset,
    wait_for_attr
)
from py_eosio.tokens import sys_token
from py_eosio.sugar import (
    collect_stdout,
    docker_open_process,
    docker_wait_process
)

from .config import * 
from .cleos_evm import CLEOSEVM


class TEVMCException(BaseException):
    ...


class TEVMController:

    def __init__(
        self,
        client = None,
        logger = None,
        log_level: str = 'info',
        debug_evm: bool = False,
        chain_name: str = 'telos-local-testnet',
        snapshot: Optional[str] = None,
        producer_key: str = '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',
        redis_tag: str = REDIS_TAG,
        rabbitmq_tag: str = RABBITMQ_TAG,
        elasticsearch_tag: str = ELASTICSEARCH_TAG,
        kibana_tag: str = KIBANA_TAG,
        eosio_tag: str = EOSIO_TAG,
        beats_tag: str = BEATS_TAG,
        hyperion_tag: str = HYPERION_TAG
    ):
        self.client = docker.from_env()
        self.root_pwd = Path(__file__).parent.parent.resolve()
        self.exit_stack = ExitStack()
        
        self.chain_name = chain_name
        self.snapshot = snapshot
        self.logger = logger

        if logger is None:
            self.logger = logging.getLogger()
            self.logger.setLevel(log_level.upper())

        self.debug_evm = debug_evm
        self.producer_key = producer_key

        splt_chain_name = chain_name.split('-')
        if len(splt_chain_name) < 2:
            raise TEVMController(f'Wrong chain_name format! {chain_name}')

        self.chain_type = splt_chain_name[1]
        chain_types = ['local', 'testnet', 'mainnet']
        if self.chain_type not in chain_types:
            raise ValueError(f'Chain type must be one of {chain_types}')

        self.network = None

        self._redis_container = None
        self._redis_container_tag = redis_tag

        self._rabbitmq_container = None
        self._rabbitmq_container_tag = rabbitmq_tag

        self._elasticsearch_container = None
        self._elasticsearch_container_tag = elasticsearch_tag

        self._kibana_container = None
        self._kibana_container_tag = kibana_tag

        self._eosio_node_container = None
        self._eosio_node_container_tag = eosio_tag

        self._beats_container = None
        self._beats_container_tag = beats_tag

        self._hyperion_indexer_container = None
        self._hyperion_indexer_container_tag = hyperion_tag
        self._hyperion_api_container = None
        self._hyperion_api_container_tag = hyperion_tag

    def init_network(self):
        """Try to attach to already created default network or create.
        """

        try:
            self.network = self.client.networks.get(DEFAULT_NETWORK_NAME)
        except docker.errors.NotFound:
            self.network = self.client.networks.create(
                DEFAULT_NETWORK_NAME,
                driver='bridge',
                labels=DEFAULT_DOCKER_LABEL)

    @contextmanager
    def temporary_directory(self, dir: Path):
        """Manages a temporary directory, creates it, gives permissions then
        yields the directory, on control return deletes it ignoring errors.
        """

        shutil.rmtree(dir, ignore_errors=True)
        dir.mkdir(parents=True)
        self.logger.info(f'created temp dir: {dir}')
        dir.chmod(0o777)

        yield dir
        shutil.rmtree(dir, ignore_errors=True)
        self.logger.info(f'deleted temp dir: {dir}')

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
        container = None
        try:
            # check if there already is a container running from that image
            found = self.client.containers.list(
                filters={'name': name, 'status': 'running'})

            if len(found) > 0:
                raise TEVMCException(
                    f'Container from image \'{image}\' is already running.')

            # check if image is present
            local_images = []
            for img in self.client.images.list(all=True):
                local_images += img.tags

            if image not in local_images:
                """Attempt to pull from remote
                """
                splt_image = image.split(':')
                if len(splt_image) == 2:
                    repo, tag = splt_image
                else:
                    raise ValueError(
                        f'Expected \'{image}\' to have \'repo:tag\' format.') 

                try:
                    updates = {}
                    for update in self.client.api.pull(
                        repo, tag=tag, stream=True, decode=True
                    ):
                        if 'id' in update:
                            _id = update['id']
                        if _id not in updates or (updates[_id] != update['status']):
                            updates[_id] = update['status']
                            self.logger.info(f'{_id}: {update["status"]}')

                except docker.errors.ImageNotFound:
                   raise TEVMCException(f'Image \'{image}\' not found on either local or'
                        ' remote repos. Maybe consider running \'tevmc build\'')

            # finally run container
            self.logger.info(f'opening {name}...')
            container = self.client.containers.run(
                image,
                *args, **kwargs,
                name=name,
                detach=True,
                network=self.network.id,
                log_config=LogConfig(
                    type=LogConfig.types.JSON,
                    config={'max-size': '2m' }),
                remove=True,
                labels=DEFAULT_DOCKER_LABEL)
            
            self.logger.info(container.status)
            self.logger.info(f'waiting on networking check')
            ip = wait_for_attr(container, (
                'NetworkSettings', 'Networks', self.network.name, 'IPAddress'))
            self.logger.info(f'container at {ip} started')

            yield container

        finally:
            self.logger.info(f'stopping container \"{name}\"')
            try:
                if container:
                    container.stop()
            except docker.errors.APIError as e:
                self.logger.critical(e) 

            self.logger.info(f'remove image for \"{name}\"')
            # try:
            #     if container:
            #         container.remove()

            # except docker.errors.APIError as e:
            #     self.logger.critical(e)
    
    def stream_logs(self, container):
        if container is None:
            self.logger.critical("container is None")
            raise StopIteration

        for chunk in container.logs(stream=True):
            msg = chunk.decode('utf-8')
            yield msg

    def start_redis(self, port: str = '6379/tcp'):
        """Start redis container and await port init.
        """
        self._redis_container = self.exit_stack.enter_context(
            self.open_container(
                'redis',
                self._redis_container_tag,
                ports={port: port}
            )
        )

        self._redis_port = wait_for_attr(
            self._redis_container,
            ('NetworkSettings', 'Ports', port)
        )

        # for msg in self.stream_logs(self._redis_container):
        #     if 'Ready to accept connections' in msg:
        #         break

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
                self._rabbitmq_container_tag,
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

        for msg in self.stream_logs(self._rabbitmq_container):
            if 'Server startup complete' in msg:
                break

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
                self._elasticsearch_container_tag,
                environment={
                    'discovery.type': 'single-node',
                    'cluster.name': 'es-cluster',
                    'node.name': 'es01',
                    'bootstrap.memory_lock': 'true',
                    'xpack.security.enabled': 'true',
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

        for msg in self.stream_logs(self._elasticsearch_container):
            if 'recovered [0] indices into cluster' in msg:
                break

    def start_kibana(self, port: str = '5601/tcp'):
        """Start kibana container and await port init.
        """
        self._kibana_container = self.exit_stack.enter_context(
            self.open_container(
                'kibana',
                self._kibana_container_tag,
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

        #for msg in self.stream_logs(self._kibana_container):
        #    if 'http server running at' in msg:
        #        break

    def start_eosio_node(
        self,
        chain_type: str,  # local, testnet, mainnet,
        snapshot: Optional[str] = None,
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
        self.logger.info(f'starting {chain_type} eosio node.')

        # search for volume and delete if exists
        try:
            vol = self.client.volumes.get(EOSIO_VOLUME_NAME)
            vol.remove()

        except docker.errors.NotFound:
            pass

        except docker.errors.APIError as api_err:
            if api_err.status_code == 409:
                raise TEVMCException(
                    'eosio_volume in use, docker envoirment messy, cleanup '
                    'volumes and rerun.')

        self._eosio_volume = self.client.volumes.create(
            name=EOSIO_VOLUME_NAME,
            labels=DEFAULT_DOCKER_LABEL)

        self._eosio_volume_path = Path(self.client.api.inspect_volume(
            self._eosio_volume.name)['Mountpoint'])

        env = {
            'NODEOS_DATA_DIR': '/mnt/dev/data',
            'NODEOS_CONFIG': f'/root/config.{chain_type}.ini',
            'NODEOS_LOG_PATH': DEFAULT_NODEOS_LOG_PATH
        }
        if snapshot:
            env['NODEOS_SNAPSHOT'] = snapshot

        else:
            env['NODEOS_GENESIS_JSON'] = f'/root/genesis.{chain_type}.json'

        # open container
        self._eosio_node_container = self.exit_stack.enter_context(
            self.open_container(
                'eosio_nodeos',
                self._eosio_node_container_tag,
                # command=[
                #     '/bin/bash', '-c',
                #     'trap : TERM INT; service cron start; sleep infinity & wait'
                # ],
                environment=env,
                ports=ports,
                volumes=[
                    f'{self._eosio_volume.name}:/mnt/dev/data'
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

        exec_id, exec_stream = docker_open_process(
            self.client, self._eosio_node_container,
            ['/bin/bash', '-c', 
                'while true; do logrotate /etc/logrotate.conf; sleep 60; done'])

        # setup cleos wrapper
        cleos = CLEOSEVM(
            self.client,
            self._eosio_node_container,
            logger=self.logger)

        # init wallet
        cleos.start_keosd(
            '-c',
            '/root/eosio-wallet/config.ini') 
        cleos.setup_wallet(self.producer_key)

        if chain_type == 'local':
            # await for nodeos to produce a block
            cleos.wait_produced(from_file=DEFAULT_NODEOS_LOG_PATH)
            try:
                cleos.boot_sequence(
                    sys_contracts_mount='/opt/eosio/bin/contracts')

            except AssertionError:
                ec, out = cleos.gather_nodeos_output()
                self.logger.critical(f'nodeos exit code: {ec}')
                self.logger.critical(f'nodeos output:\n{out}\n')
                sys.exit(1)

        else:
            # await for nodeos to receive a block from peers
            cleos.wait_received(from_file=DEFAULT_NODEOS_LOG_PATH)

        self.logger.info(cleos.get_info())

        self.cleos = cleos
    
    def deploy_evm(
        self,
        debug: bool = False,
        start_bytes: int = 1073741824,
        target_free: int = 1073741824,
        min_buy: int = 20000,
        fee_transfer_pct: int = 100,
        gas_per_byte: int = 69
    ):
    
        # create evm accounts
        self.cleos.new_account(
            'eosio.evm',
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L',
            ram=start_bytes)

        self.cleos.new_account(
            'fees.evm',
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L',
            ram=100000)

        ram_price_post = self.cleos.get_ram_price()

        start_cost = Asset(ram_price_post.amount * start_bytes, sys_token)

        self.cleos.new_account(
            'rpc.evm',
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L',
            cpu='10000.0000 TLOS',
            net='10000.0000 TLOS',
            ram=100000)

        contract_path = '/opt/eosio/bin/contracts/eosio.evm'
        if debug:
            contract_path += '/debug'

        self.cleos.deploy_contract(
            'eosio.evm', contract_path,
            privileged=True,
            create_account=False)

        ec, out = self.cleos.push_action(
            'eosio.evm',
            'init',
            [
                start_bytes,
                start_cost,
                target_free,
                min_buy,
                fee_transfer_pct,
                gas_per_byte
            ], 'eosio.evm@active')

    def create_test_evm_account(
        self,
        name: str = 'evmuser1',
        data: str = 'foobar',
        truffle_addr: str = '0xf79b834a37f3143f4a73fc3934edac67fd3a01cd'
    ):
        self.cleos.new_account(
            name,
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L')
        self.cleos.create_evm_account(name, data)
        quantity = Asset(111000000, sys_token)
        
        self.cleos.transfer_token('eosio', name, quantity, ' ')
        self.cleos.transfer_token(name, 'eosio.evm', quantity, 'Deposit')

        eth_addr = self.cleos.eth_account_from_name(name)
        assert eth_addr 

        self.logger.info(f'{name}: {eth_addr}')

        addr_amount_pairs = [
            (truffle_addr, 100000000),
            ('0xc51fE232a0153F1F44572369Cefe7b90f2BA08a5', 100000),
            ('0xf922CC0c6CA8Cdbf5330A295a11A40911FDD3B6e', 10000),
            ('0xCfCf671eBE5880d2D7798d06Ff7fFBa9bdA1bE64', 10000),
            ('0xf6E6c4A9Ca3422C2e4F21859790226DC6179364d', 10000),
            ('0xe83b5B17AfedDb1f6FF08805CE9A4d5eDc547Fa2', 10000),
            ('0x97baF2200Bf3053cc568AA278a55445059dF2d97', 10000),
            ('0x2e5A2c606a5d3244A0E8A4C4541Dfa2Ec0bb0a76', 10000),
            ('0xb4A541e669D73454e37627CdE2229Ad208d19ebF', 10000),
            ('0x717230bA327FE8DF1E61434D99744E4aDeFC53a0', 10000),
            ('0x52b7c04839506427620A2B759c9d729BE0d4d126', 10000)
        ]

        for addr, amount in addr_amount_pairs:
            ec, out = self.cleos.eth_transfer(
                'evmuser1',
                eth_addr,
                addr,
                Asset(amount, sys_token)
            )
            time.sleep(0.05)
            assert ec == 0


    def start_hyperion_indexer(self, chain: str):
        """Start hyperion_indexer container and await port init.
        """

        self._indexer_logs_volume = self.client.volumes.create(
            name=HYPERION_INDEXER_LOG_VOLUME,
            labels=DEFAULT_DOCKER_LABEL)

        self._hyperion_indexer_container = self.exit_stack.enter_context(
            self.open_container(
                'hyperion-indexer',
                self._hyperion_indexer_container_tag,
                command=[
                    '/bin/bash', '-c',
                    f'/root/scripts/run-hyperion.sh {chain}-indexer'
                ],
                volumes={
                    self._indexer_logs_volume.name:
                        {'bind': '/root/.pm2/logs', 'mode': 'rw'}
                },
                force_unique=True
            )
        )

        # for msg in self.stream_logs(self._hyperion_indexer_container):
        #    if '02_continuous_reader] Websocket connected!' in msg:
        #        break

    def start_hyperion_api(self, chain: str, port: str = '7000/tcp'):
        """Start hyperion_api container and await port init.
        """

        self._api_logs_volume = self.client.volumes.create(
            name=HYPERION_API_LOG_VOLUME,
            labels=DEFAULT_DOCKER_LABEL)

        self._hyperion_api_container = self.exit_stack.enter_context(
            self.open_container(
                'hyperion-api',
                self._hyperion_api_container_tag,
                command=[
                    '/bin/bash', '-c',
                    f'/root/scripts/run-hyperion.sh {chain}-api'
                ],
                volumes={
                    self._api_logs_volume.name:
                        {'bind': '/root/.pm2/logs', 'mode': 'rw'}
                },
                force_unique=True,
                ports={port: port}
            )
        )

        self._hyperion_api_port = wait_for_attr(
            self._hyperion_api_container,
            ('NetworkSettings', 'Ports', port)
        )

        for msg in self.stream_logs(self._hyperion_api_container):
            if 'api ready' in msg:
                break

    def setup_index_patterns(self, patterns: List[str]):
        for pattern_title in patterns:
            self.logger.info(
                f'registering index pattern \'{pattern_title}\'')
            while True:
                try:
                    resp = requests.post(
                        f'http://localhost:{self._kibana_port[0]["HostPort"]}'
                        '/api/index_patterns/index_pattern',
                        auth=HTTPBasicAuth('elastic', 'password'),
                        headers={'kbn-xsrf': 'true'},
                        json={
                            "index_pattern" : {
                                "title": pattern_title,
                                "timeFieldName": "@timestamp"
                            }
                        }).json()
                    self.logger.debug(resp)

                except requests.exceptions.ConnectionError:
                    self.logger.warning('can\'t reach kibana, retry in 3 sec...')

                except requests.exceptions.JSONDecodeError:
                    self.logger.info('kibana server not ready, retry in 3 sec...')

                else:
                    break

                time.sleep(3)
            self.logger.info('registered.')

    def start_beats(self):
        self._beats_container = self.exit_stack.enter_context(
            self.open_container(
                'beats',
                self._beats_container_tag,
                volumes={
                    self._indexer_logs_volume.name:
                        {'bind': '/root/indexer-logs', 'mode': 'ro'},
                    self._api_logs_volume.name:
                        {'bind': '/root/api-logs', 'mode': 'ro'}
                },
                environment={
                    'CHAIN_TYPE': self.chain_type
                }
            )
        )

        exec_id, exec_stream = docker_open_process(
            self.client,
            self._beats_container,
            ['filebeat', 'setup', '--pipelines'])

        ec, out = docker_wait_process(self.client, exec_id, exec_stream)
        assert ec == 0

        self.setup_index_patterns(
            [f'{self.chain_name}-action-*', 'filebeat-*'])

        
    def __enter__(self):
        is_local = self.chain_type == 'local'

        self.init_network()

        self.start_redis()
        self.start_rabbitmq()
        self.start_elasticsearch()
        self.start_kibana()

        containers = [
            self._redis_container,
            self._rabbitmq_container,
            self._elasticsearch_container,
            self._kibana_container
        ]

        for container in containers:
            container.update(blkio_weight=10)

        self.start_eosio_node(
            self.chain_type,
            snapshot=self.snapshot)

        if is_local:
            self.deploy_evm(
                debug=self.debug_evm)

        containers.append(self._eosio_node_container)
        self._eosio_node_container.update(blkio_weight=10)

        time.sleep(2)

        self.start_hyperion_indexer(self.chain_name)
        self.start_hyperion_api(self.chain_name)

        for container in containers:
            container.update(blkio_weight=500)

        self.start_beats()

        self.cleos.init_w3()

        if is_local:
            self.create_test_evm_account()

        return self

    def __exit__(self, type, value, traceback):

        # log dump
        pid = os.getpid()

        def log_dump(container) -> str:
            path = f'/tmp/{container.name}-{pid}.log'
            self.logger.info(path)
            with open(path, 'wb+') as logfile:
                logfile.write(container.logs())
        
        log_dump(self._hyperion_api_container)
        log_dump(self._hyperion_indexer_container)

        self.exit_stack.pop_all().close()
        self.network.remove()

