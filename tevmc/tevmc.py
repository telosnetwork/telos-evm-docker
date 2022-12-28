#!/usr/bin/env python3

import re
import os
import sys
import time
import shutil
import signal
import logging

from signal import SIGINT
from typing import List, Dict, Optional
from pathlib import Path
from contextlib import contextmanager, ExitStack

import docker
import requests
import simplejson

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
        root_pwd: Optional[Path] = None,
        wait: bool = True,
        full: bool = True 
    ):
        self.pid = os.getpid()
        self.config = config
        self.client = docker.from_env()
        self.exit_stack = ExitStack()
        self.wait = wait
        self.full = full 

        if not root_pwd:
            self.root_pwd = Path().resolve()
        else:
            self.root_pwd = root_pwd

        self.docker_wd = self.root_pwd / 'docker'

        self.is_relaunch = (
            self.docker_wd / 
            config['nodeos']['docker_path'] / 
            config['nodeos']['data_dir_host'] /
            'blocks').is_dir()

        self.chain_name = config['hyperion']['chain']['name']
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
           
            container.reload()

            self.logger.info(container.status)
            yield container

        finally:
            self.logger.info(f'stopping container \"{name}\"')
            try:
                if container:
                    for i in range(3):
                        container.stop()
            except docker.errors.APIError as e:
                ...

            self.logger.info('stopped.')

    
    def stream_logs(self, container):
        if container is None:
            self.logger.critical("container is None")
            raise StopIteration

        for chunk in container.logs(stream=True):
            msg = chunk.decode('utf-8')
            yield msg

    @contextmanager
    def must_keep_running(self, container: str):
        yield
        
        container = self.containers[container]
        container.reload()

        if container.status != 'running':
            self.logger.critical(f'container status: {container.status}, log dump:')
            try:
                self.logger.critical(container.logs().decode('utf-8'))

            except docker.errors.NotFound:
                self.logger.critical('couldn\'t access logs.')

            raise TEVMCException(f'{container.name} is not running')

    def start_redis(self):
        with self.must_keep_running('redis'):
            config = self.config['redis']
            docker_dir = self.docker_wd / config['docker_path']

            conf_dir = docker_dir / config['conf_dir']
            data_dir = docker_dir / config['data_dir']

            data_dir.mkdir(parents=True, exist_ok=True)

            self.mounts['redis'] = [
                Mount('/root', str(conf_dir.resolve()), 'bind'),
                Mount('/data', str(data_dir.resolve()), 'bind')
            ]

            self.containers['redis'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                    mounts=self.mounts['redis']
                ) 
            )

            for msg in self.stream_logs(self.containers['redis']):
                self.logger.info(msg.rstrip())
                if 'Ready to accept connections' in msg:
                    break

    def start_elasticsearch(self):
        with self.must_keep_running('elasticsearch'):
            config = self.config['elasticsearch']
            docker_dir = self.docker_wd / config['docker_path']

            data_dir = docker_dir / config['data_dir']
            logs_dir = docker_dir / config['logs_dir']

            data_dir.mkdir(parents=True, exist_ok=True)
            logs_dir.mkdir(parents=True, exist_ok=True)

            self.mounts['elasticsearch'] = [
                Mount('/home/elasticsearch/logs', str(logs_dir.resolve()), 'bind'),
                Mount('/home/elasticsearch/data', str(data_dir.resolve()), 'bind')
            ]

            self.containers['elasticsearch'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                    environment={
                        'discovery.type': 'single-node',
                        'cluster.name': 'es-cluster',
                        'node.name': 'es01',
                        'bootstrap.memory_lock': 'true',
                        'xpack.security.enabled': 'true',
                        'ES_JAVA_OPTS': '-Xms2g -Xmx2g',
                        'ES_NETWORK_HOST': '0.0.0.0'
                    },
                    mounts=self.mounts['elasticsearch']
                )
            )

            for msg in self.stream_logs(self.containers['elasticsearch']):
                self.logger.info(msg.rstrip())
                if ' indices into cluster_state' in msg:
                    break

            if not self.is_relaunch:
                # setup password for elastic user
                resp = requests.put(
                    f'http://{config["host"]}/_xpack/security/user/elastic/_password',
                    auth=('elastic', 'temporal'),
                    json={'password': config['elastic_pass']})
            
                self.logger.info(resp.text)
                assert resp.status_code == 200

                # setup user
                resp = requests.put(
                    f'http://{config["host"]}/_xpack/security/user/{config["user"]}',
                    auth=('elastic', config['elastic_pass']),
                    json={
                        'password': config['pass'],
                        'roles': [ 'superuser' ]
                    })
        
                self.logger.info(resp.text)
                assert resp.status_code == 200

    def stop_elasticsearch(self):
        self.containers['elasticsearch'].kill(signal.SIGTERM)

        for msg in self.stream_logs(
            self.containers['elasticsearch']):
            continue

    def start_kibana(self):
        with self.must_keep_running('kibana'):
            config = self.config['kibana']
            config_elastic = self.config['elasticsearch']
            docker_dir = self.docker_wd / config['docker_path']
            data_dir = docker_dir / config['data_dir']
            conf_dir = docker_dir / config['conf_dir']

            data_dir.mkdir(parents=True, exist_ok=True)

            self.mounts['kibana'] = [
                Mount('/usr/share/kibana/config', str(conf_dir.resolve()), 'bind'),
                Mount('/data', str(data_dir.resolve()), 'bind')
            ]

            self.containers['kibana'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                    environment={
                        'ELASTICSEARCH_HOSTS': f'http://{config_elastic["host"]}',
                        'ELASTICSEARCH_USERNAME': config_elastic['user'],
                        'ELASTICSEARCH_PASSWORD': config_elastic['pass']
                    },
                    mounts=self.mounts['kibana']
                )
            )

    def start_nodeos(self):
        """Start eosio_nodeos container.

        - Initialize CLEOS wrapper and setup keosd & wallet.
        - Launch nodeos with config.ini
        - Wait for nodeos to produce blocks
        - Create evm accounts and deploy contract
        """
        with self.must_keep_running('nodeos'):
            config = self.config['nodeos']
            docker_dir = self.docker_wd / config['docker_path']

            data_dir_guest = config['data_dir_guest']
            data_dir_host = docker_dir / config['data_dir_host']

            conf_dir = docker_dir / config['conf_dir']
            contracts_dir = docker_dir / config['contracts_dir']

            data_dir_host.mkdir(parents=True, exist_ok=True)

            self.mounts['nodeos'] = [
                Mount('/root', str(conf_dir.resolve()), 'bind'),
                Mount('/opt/eosio/bin/contracts', str(contracts_dir.resolve()), 'bind'),
                Mount(data_dir_guest, str(data_dir_host.resolve()), 'bind')
            ]

            if 'mounts' in config:
                self.mounts['nodeos'] += [
                    Mount(m['target'], m['source'], 'bind') for m in config['mounts']]

            env = {
                'NODEOS_DATA_DIR': config['data_dir_guest'],
                'NODEOS_CONFIG': f'/root/config.ini',
                'NODEOS_LOG_PATH': config['log_path'],
                'NODEOS_LOGCONF': '/root/logging.json',
                'KEOSD_LOG_PATH': '/root/keosd.log',
                'KEOSD_CONFIG': '/root/keosd_config.ini'
            }

            if not self.is_relaunch:
                if 'snapshot' in config:
                    env['NODEOS_SNAPSHOT'] = config['snapshot']

                elif 'genesis' in config: 
                    env['NODEOS_GENESIS_JSON'] = f'/root/genesis/{config["genesis"]}.json'

            self.logger.info(f'is relaunch: {self.is_relaunch}')

            # open container
            self.containers['nodeos'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                    environment=env,
                    mounts=self.mounts['nodeos']
                )
            )

            # for msg in self.stream_logs(self.containers['nodeos']):
            #     self.logger.info(msg.rstrip())
            #     if 'configured http to listen on' in msg:
            #         break

            #     elif 'Incorrect plugin configuration' in msg:
            #         raise TEVMCException('Nodeos bootstrap error.')

            exec_id, exec_stream = docker_open_process(
                self.client, self.containers['nodeos'],
                ['/bin/bash', '-c', 
                    'while true; do logrotate /root/logrotate.conf; sleep 60; done'])

            nodeos_api_port = config['ini']['http_addr'].split(':')[1]
            hyperion_api_port = self.config['hyperion']['chain']['router_port']

            cleos_url = f'http://127.0.0.1:{nodeos_api_port}'
            hyperion_api_url = f'http://127.0.0.1:{hyperion_api_port}'

            # setup cleos wrapper
            cleos = CLEOSEVM(
                self.client,
                self.containers['nodeos'],
                logger=self.logger,
                url=cleos_url,
                hyperion_api_endpoint=hyperion_api_url)

            self.cleos = cleos

            # manual start stuff

            # init wallet
            cleos.start_keosd(
                '-c',
                '/root/keosd_config.ini')

            nodeos_params = {
                'data_dir': config['data_dir_guest'],
                'logfile': config['log_path'],
                'logging_cfg': '/root/logging.json'
            }

            if not self.is_relaunch:
                if 'snapshot' in config:
                    nodeos_params['snapshot'] = config['snapshot']

                elif 'genesis' in config:
                    nodeos_params['genesis'] = f'/root/genesis/{config["genesis"]}.json'

            cleos.start_nodeos_from_config(
                '/root/config.ini',
                state_plugin=True,
                **nodeos_params
            )

            nodeos_params = {
                'data_dir': config['data_dir_guest'],
                'logfile': config['log_path'],
                'logging_cfg': '/root/logging.json'
            }

            if not self.is_relaunch:
                if 'snapshot' in config:
                    nodeos_params['snapshot'] = config['snapshot']

                elif 'genesis' in config:
                    nodeos_params['genesis'] = f'/root/genesis/{config["genesis"]}.json'

            output = cleos.start_nodeos_from_config(
                '/root/config.ini',
                state_plugin=True,
                is_local=self.is_local,
                **nodeos_params
            )
            if self.is_local:
                # await for nodeos to produce a block
                cleos.wait_blocks(4)

                self.is_fresh = 'Initializing fresh blockchain' in output

                if self.is_fresh:
                    cleos.setup_wallet(self.producer_key)

                    try:
                        cleos.boot_sequence(
                            sys_contracts_mount='/opt/eosio/bin/contracts',
                            verify_hash=False)

                        cleos.deploy_evm()

                    except AssertionError:
                        for msg in self.stream_logs(self.containers['nodeos']):
                            self.logger.critical(msg.rstrip()) 
                        sys.exit(1)

            self.logger.info(cleos.get_info())

    def setup_hyperion_log_mount(self):
        docker_dir = self.docker_wd / self.config['hyperion']['docker_path']
        logs_dir = docker_dir / self.config['hyperion']['logs_dir']
        conf_dir = docker_dir / self.config['hyperion']['conf_dir']

        logs_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['hyperion'] = [
            Mount('/hyperion-history-api/chains', str(conf_dir.resolve()), 'bind'),
            Mount('/root/.pm2/logs', str(logs_dir.resolve()), 'bind')
        ]

    def _get_head_block(self):
        if 'testnet' in self.chain_name:
            endpoint = 'https://testnet.telos.net'
        else:
            endpoint = 'https://mainnet.telos.net'

        resp = requests.get(f'{endpoint}/v1/chain/get_info').json()
        return resp['head_block_num']

    def await_full_index(self):
        last_indexed_block = 0
        remote_head_block = self._get_head_block()
        last_update_time = time.time()
        for line in self.stream_logs(self.containers['hyperion-indexer']):
            if 'continuous_reader' in line:
                self.logger.info(line.rstrip())
                m = re.findall(r'block_num: ([0-9]+)', line)
                if len(m) == 1:
                    last_indexed_block = int(m[0])

                delta = remote_head_block - last_indexed_block

                self.logger.info(f'waiting on indexer... delta: {delta}')

                if delta < 100:
                    break

                now = time.time()
                if now - last_update_time > 3600:
                    remote_head_block = self._get_head_block()
                    last_update_time = now

    def start_hyperion_api(self):
        with self.must_keep_running('hyperion-api'):
            config = self.config['hyperion']['api']

            self.containers['hyperion-api'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{self.config["hyperion"]["tag"]}-{self.config["hyperion"]["chain"]["name"]}',
                    command=[
                        '/bin/bash', '-c',
                        f'/root/scripts/run-hyperion.sh {self.chain_name}-api'
                    ],
                    mounts=self.mounts['hyperion']
                )
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

                except simplejson.errors.JSONDecodeError:
                    self.logger.info('kibana server not ready, retry in 3 sec...')

                else:
                    break

                time.sleep(3)
            self.logger.info('registered.')

    def start_beats(self):
        with self.must_keep_running('beats'):
            config = self.config['beats']
            config_elastic = self.config['elasticsearch']
            config_kibana = self.config['kibana']

            hyperion_docker_dir = self.docker_wd / self.config['hyperion']['docker_path']
            data_dir = hyperion_docker_dir / self.config['hyperion']['logs_dir']
            docker_dir = self.docker_wd / config['docker_path']
            conf_dir = docker_dir / config['conf_dir']

            data_dir.mkdir(parents=True, exist_ok=True)

            self.mounts['beats'] = [
                Mount('/etc/filebeat', str(conf_dir.resolve()), 'bind'),
                Mount('/root/logs', str(data_dir.resolve()), 'bind')
            ]

            self.containers['beats'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
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
                ['chown', '-R', '0:0', '/etc/filebeat/filebeat.yml'])

            ec, out = docker_wait_process(self.client, exec_id, exec_stream)
            assert ec == 0

            exec_id, exec_stream = docker_open_process(
                self.client,
                self.containers['beats'],
                ['chmod', '600', '/etc/filebeat/filebeat.yml'])

            ec, out = docker_wait_process(self.client, exec_id, exec_stream)
            assert ec == 0

            exec_id, exec_stream = docker_open_process(
                self.client,
                self.containers['beats'],
                ['filebeat', '-e'])

            time.sleep(3)

            exec_id, exec_stream = docker_open_process(
                self.client,
                self.containers['beats'],
                ['filebeat', 'setup', '--pipelines'])

            ec, out = docker_wait_process(self.client, exec_id, exec_stream)
            if ec != 0:
                self.logger.error('filebeats pipeline setup error: ')
                self.logger.error(out)

            else:
                self.logger.info('pipelines setup')


            if self.is_local:
                self.setup_index_patterns(
                    [f'{self.chain_name}-action-*', 'filebeat-*'])

    def start_telosevm_indexer(self):
        with self.must_keep_running('telosevm-indexer'):
            config = self.config['telosevm-indexer']
            config_elastic = self.config['elasticsearch']
            config_nodeos = self.config['nodeos']
            config_hyperion = self.config['hyperion']['chain']['telos-evm']

            nodeos_api_port = config_nodeos['ini']['http_addr'].split(':')[1]
            nodeos_ship_port = config_nodeos['ini']['history_endpoint'].split(':')[1]
            endpoint = f'http://127.0.0.1:{nodeos_api_port}'
            ws_endpoint = f'ws://127.0.0.1:{nodeos_ship_port}'

            bc_host = config_hyperion['indexerWebsocketHost']
            bc_port = config_hyperion['indexerWebsocketPort']

            self.containers['telosevm-indexer'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{ self.config["hyperion"]["chain"]["name"]}',
                    environment={
                        'CHAIN_NAME': self.config['hyperion']['chain']['name'],
                        'CHAIN_ID': self.config['hyperion']['chain']['chain_id'],
                        'ELASTIC_USERNAME': config_elastic['user'],
                        'ELASTIC_PASSWORD': config_elastic['pass'],
                        'ELASTIC_NODE': f'http://{config_elastic["host"]}',
                        'TELOS_ENDPOINT': endpoint,
                        'TELOS_WS_ENDPOINT': ws_endpoint,
                        'INDEXER_START_BLOCK': config["start_block"],
                        'INDEXER_STOP_BLOCK': config["stop_block"],
                        'BROADCAST_HOST': bc_host,
                        'BROADCAST_PORT': bc_port
                    }
                )
            )

            for msg in self.stream_logs(self.containers['telosevm-indexer']):
                self.logger.info(msg.rstrip())
                if 'Receiving ABI from ship' in msg:
                    break

    def start(self):
        self.start_redis()
        self.start_elasticsearch()

        if self.full:
            self.start_kibana()

        self.start_nodeos()

        self.setup_hyperion_log_mount()

        self.start_telosevm_indexer()

        # if not self.is_local and self.wait:
        #     self.await_full_index()

        self.start_hyperion_api()

        if self.full:
            self.start_beats()

        if self.is_local and self.is_fresh:
            self.cleos.create_test_evm_account()

    def stop(self):
        self.cleos.stop_nodeos(
            from_file=self.config['nodeos']['log_path'])

        self.stop_elasticsearch()

        self.exit_stack.pop_all().close()


    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
