#!/usr/bin/env python3

import os
import sys
import time
import shutil
import logging

from signal import SIGINT
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
        config: Dict[str, Dict],
        client = None,
        logger = None,
        log_level: str = 'info',
        snapshot: Optional[str] = None
    ):
        self.pid = os.getpid()
        self.config = config
        self.client = docker.from_env()
        self.root_pwd = Path().resolve()
        self.docker_wd = self.root_pwd / 'docker'
        self.exit_stack = ExitStack()
        
        self.chain_name = config['hyperion']['chain']['name']
        self.snapshot = snapshot
        self.logger = logger

        if logger is None:
            self.logger = logging.getLogger()
            self.logger.setLevel(log_level.upper())

        self.is_local = 'local' in self.chain_name
        
        if self.is_local:
            self.producer_key = config['nodeos']['ini']['sig_provider'].split(':')[-1]

        self.containers = {}
        self.mounts = {} 

    @contextmanager
    def open_container(
        self, 
        name: str,
        image: str,
        net: str = 'host',
        *args, **kwargs
    ):
        """Start a new container.
        
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
                network=net,
                log_config=LogConfig(
                    type=LogConfig.types.JSON,
                    config={'max-size': '100m' }),
                remove=True,
                labels=DEFAULT_DOCKER_LABEL)
            
            self.logger.info(container.status)
            yield container

        finally:
            self.logger.info(f'stopping container \"{name}\"')
            try:
                if container:
                    container.stop()
            except docker.errors.APIError as e:
                self.logger.critical(e) 

    
    def stream_logs(self, container):
        if container is None:
            self.logger.critical("container is None")
            raise StopIteration

        for chunk in container.logs(stream=True):
            msg = chunk.decode('utf-8')
            yield msg

    def start_redis(self):
        config = self.config['redis']
        docker_dir = self.docker_wd / config['docker_path']
        data_dir = docker_dir / config['data_dir']

        data_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['redis'] = [
            Mount('/data', str(data_dir.resolve()), 'bind')
        ]

        config = self.config['redis']
        self.containers['redis'] = self.exit_stack.enter_context(
            self.open_container(
                f'{config["name"]}-{self.pid}',
                f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                mounts=self.mounts['redis']
            ) 
        )

        wait_for_attr(
            self.containers['redis'],
            ('NetworkSettings', 'Ports', f'{config["port"]}/tcp')
        )

        # for msg in self.stream_logs(self._redis_container):
        #     if 'Ready to accept connections' in msg:
        #         break

    def start_rabbitmq(self):
        config = self.config['rabbitmq']
        docker_dir = self.docker_wd / config['docker_path']
        data_dir = docker_dir / config['data_dir']

        data_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['rabbitmq'] = [
            Mount('/var/lib/rabbitmq', str(data_dir.resolve()), 'bind')
        ]

        self.containers['rabbitmq'] = self.exit_stack.enter_context(
            self.open_container(
                f'{config["name"]}-{self.pid}',
                f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                environment={
                    'RABBITMQ_DEFAULT_USER': config['user'],
                    'RABBITMQ_DEFAULT_PASS': config['pass'],
                    'RABBITMQ_DEFAULT_VHOST': config['vhost'],
                },
                mounts=self.mounts['rabbitmq']
            )
        )

        host_port = config['host'].split(':')[-1]
        api_port = config['api'].split(':')[-1]

        wait_for_attr(
            self.containers['rabbitmq'],
            ('NetworkSettings', 'Ports', f'{host_port}/tcp')
        )

        wait_for_attr(
            self.containers['rabbitmq'],
            ('NetworkSettings', 'Ports', f'{api_port}/tcp')
        )

        for msg in self.stream_logs(self.containers['rabbitmq']):
            if 'Server startup complete' in msg:
                break

    def start_elasticsearch(self):
        config = self.config['elasticsearch']
        docker_dir = self.docker_wd / config['docker_path']
        data_dir = docker_dir / config['data_dir']

        data_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['elasticsearch'] = [
            Mount('/usr/share/elasticsearch/data', str(data_dir.resolve()), 'bind')
        ]

        self.containers['elasticsearch'] = self.exit_stack.enter_context(
            self.open_container(
                f'{config["name"]}-{self.pid}',
                f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                environment={
                    'discovery.type': 'single-node',
                    'cluster.name': 'es-cluster',
                    'node.name': 'es01',
                    'bootstrap.memory_lock': 'true',
                    'xpack.security.enabled': 'true',
                    'ES_JAVA_OPTS': '-Xms2g -Xmx2g',
                    'ES_NETWORK_HOST': '0.0.0.0',
                    'ELASTIC_USERNAME': config['user'],
                    'ELASTIC_PASSWORD': config['pass']
                },
                mounts=self.mounts['elasticsearch']
            )
        )
        port = config['host'].split(':')[-1]
        wait_for_attr(
            self.containers['elasticsearch'],
            ('NetworkSettings', 'Ports', port)
        )

        for msg in self.stream_logs(self.containers['elasticsearch']):
            # self.logger.info(msg.rstrip())
            if ' indices into cluster_state' in msg:
                break

    def start_kibana(self):
        config = self.config['kibana']
        config_elastic = self.config['elasticsearch']
        docker_dir = self.docker_wd / config['docker_path']
        data_dir = docker_dir / config['data_dir']

        data_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['kibana'] = [
            Mount('/data', str(data_dir.resolve()), 'bind')
        ]

        self.containers['kibana'] = self.exit_stack.enter_context(
            self.open_container(
                f'{config["name"]}-{self.pid}',
                f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                environment={
                    'ELASTICSEARCH_HOSTS': f'http://{config_elastic["host"]}',
                    'ELASTICSEARCH_USERNAME': config_elastic['user'],
                    'ELASTICSEARCH_PASSWORD': config_elastic['pass']
                },
                mounts=self.mounts['kibana']
            )
        )

        port = config['port']
        wait_for_attr(
            self.containers['kibana'],
            ('NetworkSettings', 'Ports', port)
        )

        #for msg in self.stream_logs(self.containers['kibana']):
        #    self.logger.info(msg.rstrip())
        #    if 'http server running at' in msg:
        #        break

    def start_nodeos(self):
        """Start eosio_nodeos container.

        - Initialize CLEOS wrapper and setup keosd & wallet.
        - Launch nodeos with config.ini
        - Wait for nodeos to produce blocks
        - Create evm accounts and deploy contract
        """
        config = self.config['nodeos']
        data_dir_guest = config['data_dir_guest']
        data_dir_host = config['data_dir_host']

        docker_dir = self.docker_wd / config['docker_path']
        data_dir = docker_dir / data_dir_host

        data_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['nodeos'] = [
            Mount(data_dir_guest, str(data_dir.resolve()), 'bind')
        ]

        env = {
            'NODEOS_DATA_DIR': config['data_dir_guest'],
            'NODEOS_CONFIG': f'/root/config.ini',
            'NODEOS_LOG_PATH': config['log_path'],
            'NODEOS_LOGCONF': '/root/logging.json'
        }

        if 'snapshot' in config:
            env['NODEOS_SNAPSHOT'] = config['snapshot']

        elif 'genesis' in config: 
            env['NODEOS_GENESIS_JSON'] = f'/root/genesis/{config["genesis"]}.json'

        # open container
        self.containers['nodeos'] = self.exit_stack.enter_context(
            self.open_container(
                f'{config["name"]}-{self.pid}',
                f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                environment=env,
                mounts=self.mounts['nodeos']
            )
        )

        #for msg in self.stream_logs(self.containers['nodeos']):
        #    self.logger.info(msg.rstrip()) 

        http_port = config['ini']['http_addr'].split(':')[-1]
        wait_for_attr(
            self.containers['nodeos'],
            ('NetworkSettings', 'Ports', http_port)
        )

        ship_port = config['ini']['history_endpoint'].split(':')[-1]
        wait_for_attr(
            self.containers['nodeos'],
            ('NetworkSettings', 'Ports', ship_port)
        )

        exec_id, exec_stream = docker_open_process(
            self.client, self.containers['nodeos'],
            ['/bin/bash', '-c', 
                'while true; do logrotate /etc/logrotate.conf; sleep 60; done'])

        # setup cleos wrapper
        cleos = CLEOSEVM(
            self.client,
            self.containers['nodeos'],
            logger=self.logger)
        self.cleos = cleos

        # init wallet
        cleos.start_keosd(
            '-c',
            '/root/eosio-wallet/config.ini') 

        if self.is_local:
            cleos.setup_wallet(self.producer_key)

            # await for nodeos to produce a block
            cleos.wait_produced()
            cleos.wait_blocks(4)

            try:
                cleos.boot_sequence(
                    sys_contracts_mount='/opt/eosio/bin/contracts')

                cleos.deploy_evm()

            except AssertionError:
                ec, out = cleos.gather_nodeos_output()
                self.logger.critical(f'nodeos exit code: {ec}')
                self.logger.critical(f'nodeos output:\n{out}\n')
                sys.exit(1)

        else:
            # await for nodeos to receive a block from peers
            cleos.wait_received()

        self.logger.info(cleos.get_info())

    def setup_hyperion_log_mount(self):
        docker_dir = self.docker_wd / self.config['hyperion']['docker_path']
        data_dir = docker_dir / self.config['hyperion']['log_dir']

        data_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['hyperion'] = [
            Mount('/root/.pm2/logs', str(data_dir.resolve()), 'bind')
        ]

    def await_full_index(self):
        while True:
            try:
                hhealth = self.cleos.hyperion_health()['health']

                edata = {}
                ndata = {}
                for service in hhealth:
                    if service['service'] == 'Elasticsearch':
                        edata = service['service_data']

                    if service['service'] == 'NodeosRPC':
                        ndata = service['service_data']

                delta = ndata['last_irreversible_block'] - edata['last_indexed_block']

                self.logger.info(f'waiting on indexer... delta: {delta}')

                if delta < 100:
                    break

            except requests.exceptions.ConnectionError:
                self.logger.warning('connection error... retry...') 

            time.sleep(10)
    
    def start_hyperion_indexer(self):
        config = self.config['hyperion']['indexer']

        self.containers['hyperion-indexer'] = self.exit_stack.enter_context(
            self.open_container(
                f'{config["name"]}-{self.pid}',
                f'{self.config["hyperion"]["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                command=[
                    '/bin/bash', '-c',
                    f'/root/scripts/run-hyperion.sh {self.chain_name}-indexer'
                ],
                mounts=self.mounts['hyperion']
            )
        )

        # for msg in self.stream_logs(self._hyperion_indexer_container):
        #    if '02_continuous_reader] Websocket connected!' in msg:
        #        break

    def start_hyperion_api(self, port: str = '7000/tcp'):
        """Start hyperion_api container and await port init.
        """
        config = self.config['hyperion']['api']

        self.containers['hyperion-api'] = self.exit_stack.enter_context(
            self.open_container(
                f'{config["name"]}-{self.pid}',
                f'{self.config["hyperion"]["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                command=[
                    '/bin/bash', '-c',
                    f'/root/scripts/run-hyperion.sh {self.chain_name}-api'
                ],
                mounts=self.mounts['hyperion']
            )
        )

        wait_for_attr(
            self.containers['hyperion-api'],
            ('NetworkSettings', 'Ports', port)
        )

        for msg in self.stream_logs(self.containers['hyperion-api']):
            self.logger.info(msg.rstrip())
            if 'api ready' in msg:
                break

    def setup_index_patterns(self, patterns: List[str]):
        kibana_port = self.config['kibana']['port']

        for pattern_title in patterns:
            self.logger.info(
                f'registering index pattern \'{pattern_title}\'')
            while True:
                try:
                    resp = requests.post(
                        f'http://localhost:{kibana_port}'
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
        config = self.config['beats']
        config_elastic = self.config['elasticsearch']
        config_kibana = self.config['kibana']

        docker_dir = self.docker_wd / self.config['hyperion']['docker_path']
        data_dir = docker_dir / self.config['hyperion']['log_dir']

        data_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['beats'] = [
            Mount('/root/logs', str(data_dir.resolve()), 'bind')
        ]

        self.containers['beats'] = self.exit_stack.enter_context(
            self.open_container(
                f'{config["name"]}-{self.pid}',
                f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                environment={
                    'CHAIN_NAME': self.chain_name,
                    'ELASTIC_USER': config_elastic['user'],
                    'ELASTIC_PASS': config_elastic['pass'],
                    'ELASTIC_HOST': config_elastic['host'],
                    'KIBANA_HOST': f'localhost:{config_kibana["port"]}'
                },
                mounts=self.mounts['beats']
            )
        )

        exec_id, exec_stream = docker_open_process(
            self.client,
            self.containers['beats'],
            ['filebeat', 'setup', '--pipelines'])

        ec, out = docker_wait_process(self.client, exec_id, exec_stream)
        self.logger.info(out)
        assert ec == 0

        if self.is_local:
            self.setup_index_patterns(
                [f'{self.chain_name}-action-*', 'filebeat-*'])

        
    def __enter__(self):
        self.start_redis()
        self.start_rabbitmq()
        self.start_elasticsearch()
        self.start_kibana()
        self.start_nodeos()

        self.setup_hyperion_log_mount()
        self.start_hyperion_indexer()

        # self.await_full_index()

        self.start_hyperion_api()

        self.start_beats()

        if self.is_local:
            self.cleos.create_test_evm_account()

        return self

    def __exit__(self, type, value, traceback):

        # gracefull nodeos exit
        # self.containers['nodeos'].kill(signal=SIGINT)
        exec_id, exec_stream = docker_open_process(
            self.client,
            self.containers['nodeos'],
            ['pkill', 'nodeos'])

        ec, out = docker_wait_process(self.client, exec_id, exec_stream)
        self.logger.info(ec, out)

        for msg in self.stream_logs(self.containers['nodeos']):
            self.logger.info(msg.rstrip())
            if 'nodeos successfully exiting' in msg:
                break
        
        self.exit_stack.pop_all().close()

