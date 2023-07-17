#!/usr/bin/env python3

import re
import os
import sys
import time
import shutil
import signal
import string
import logging

from signal import SIGINT
from typing import List, Dict, Optional
from pathlib import Path
from websocket import create_connection
from contextlib import contextmanager, ExitStack

import docker
import requests
import simplejson

from web3 import Web3
from docker.types import LogConfig, Mount
from requests.auth import HTTPBasicAuth
from leap.sugar import (
    Asset,
    wait_for_attr
)
from leap.sugar import (
    collect_stdout,
    docker_open_process,
    docker_wait_process,
    download_latest_snapshot
)

from .config import *
from .cleos_evm import CLEOSEVM


class TEVMCException(BaseException):
    ...


class TEVMController:

    def __init__(
        self,
        config: Dict[str, Dict],
        logger = None,
        log_level: str = 'info',
        root_pwd: Optional[Path] = None,
        wait: bool = True,
        services: List[str] = [
            'redis',
            'elastic',
            'kibana',
            'nodeos',
            'indexer',
            'rpc',
            'beats'
        ],
        from_latest: bool = False
    ):
        self.pid = os.getpid()
        self.config = config
        self.client = docker.from_env()
        self.exit_stack = ExitStack()
        self.wait = wait
        self.services = services
        self.nodeos_logfile = None
        self.nodeos_logproc = None

        if not root_pwd:
            self.root_pwd = Path().resolve()
        else:
            self.root_pwd = root_pwd

        self.docker_wd = self.root_pwd / 'docker'

        self.is_nodeos_relaunch = (
            self.docker_wd /
            config['nodeos']['docker_path'] /
            config['nodeos']['data_dir_host'] /
            'blocks').is_dir()

        self.is_elastic_relaunch = (
            self.docker_wd /
            config['elasticsearch']['docker_path'] /
            config['elasticsearch']['data_dir'] /
            'nodes').is_dir()

        self.chain_name = config['telos-evm-rpc']['elastic_prefix']
        self.logger = logger

        if logger is None:
            self.logger = logging.getLogger()
            self.logger.setLevel(log_level.upper())

        self.is_fresh = True
        self.is_local = (
            ('testnet' not in self.chain_name) and
            ('mainnet' not in self.chain_name)
        )

        if self.is_local:
            self.producer_key = config['nodeos']['ini']['sig_provider'].split(':')[-1]

        else:
            if from_latest:
                network = 'telos'
                if 'testnet' in self.chain_name:
                    network = 'telostest'

                block_num, snap_path = download_latest_snapshot(
                    self.docker_wd /
                    config['nodeos']['docker_path'] /
                    config['nodeos']['conf_dir'],
                    network=network
                )

                self.config['nodeos']['snapshot'] = f'/root/{snap_path.name}'

                # native start block
                start_block = block_num + 100

                self.config['telosevm-translator']['start_block'] = start_block
                self.config['telosevm-translator']['deploy_block'] = start_block

                # query v2 api to get evm delta
                resp = requests.get(
                    self.config['nodeos']['v2_api'] + '/v2/history/get_deltas',
                    params={
                        'limit': 1,
                        'code': 'eosio',
                        'scope': 'eosio',
                        'table': 'global'
                    }
                )
                self.logger.info(resp)
                self.logger.info(resp.text)
                self.logger.info(resp.json())
                assert resp.status_code == 200
                delta_resp = resp.json()
                delta = delta_resp['deltas'][0]

                evm_delta = delta['block_num'] - delta['data']['block_num']
                self.logger.info(f'calculated evm delta: {evm_delta}')

                # get eth hash
                w3 = Web3(Web3.HTTPProvider(
                    self.config['telos-evm-rpc']['remote_endpoint']))

                evm_start_block = start_block - evm_delta - 1

                prev_hash = (w3.eth.get_block(evm_start_block - 1)['hash']).hex()
                if prev_hash[:2] == '0x':
                    prev_hash = prev_hash[2:]

                self.config['telosevm-translator']['prev_hash'] = prev_hash

                # dump edited config file
                with open(self.root_pwd / 'tevmc.json', 'w+') as uni_conf:
                    uni_conf.write(json.dumps(self.config, indent=4))


        self.containers = {}
        self.mounts = {}

    @contextmanager
    def open_container(
        self,
        name: str,
        image: str,
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

            # darwin arch doesn't support host networking mode...
            if sys.platform == 'darwin':
                # set to bridge, and connect to our custom virtual net after Launch
                # this way we can set the ip addr
                kwargs['network'] = 'bridge'

            elif 'linux' in sys.platform:
                kwargs['network'] = 'host'

            else:
                raise OSError('Unsupported network architecture')

            # finally run container
            self.logger.info(f'opening {name}...')
            container = self.client.containers.run(
                image,
                *args, **kwargs,
                name=name,
                detach=True,
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

            redis_port = config['port']

            more_params = {}
            if sys.platform == 'darwin':
                more_params['ports'] = {f'{redis_port}/tcp': redis_port}

            self.containers['redis'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.chain_name}',
                    mounts=self.mounts['redis'],
                    **more_params
                )
            )

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['redis'],
                    ipv4_address=config['virtual_ip']
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

            es_port = int(config['host'].split(':')[-1])

            more_params = {}
            if sys.platform == 'darwin':
                more_params['ports'] = {f'{es_port}/tcp': es_port}

            self.containers['elasticsearch'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.chain_name}',
                    environment={
                        'discovery.type': 'single-node',
                        'cluster.name': 'es-cluster',
                        'node.name': 'es01',
                        'bootstrap.memory_lock': 'true',
                        'xpack.security.enabled': 'true',
                        'ES_JAVA_OPTS': '-Xms2g -Xmx2g',
                        'ES_NETWORK_HOST': '0.0.0.0'
                    },
                    mounts=self.mounts['elasticsearch'],
                    **more_params
                )
            )

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['elasticsearch'],
                    ipv4_address=config['virtual_ip']
                )

            for msg in self.stream_logs(self.containers['elasticsearch']):
                self.logger.info(msg.rstrip())
                if ' indices into cluster_state' in msg:
                    break

            if not self.is_elastic_relaunch:
                es_endpoint = f'127.0.0.1:{es_port}'

                # setup password for elastic user
                resp = requests.put(
                    f'http://{es_endpoint}/_xpack/security/user/elastic/_password',
                    auth=('elastic', 'temporal'),
                    json={'password': config['elastic_pass']})

                self.logger.info(resp.text)
                assert resp.status_code == 200

                # setup user
                resp = requests.put(
                    f'http://{es_endpoint}/_xpack/security/user/{config["user"]}',
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

            kibana_port = config['port']

            more_params = {}
            if sys.platform == 'darwin':
                more_params['ports'] = {f'{kibana_port}/tcp': kibana_port}

            self.containers['kibana'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.chain_name}',
                    environment={
                        'ELASTICSEARCH_HOSTS': f'http://{config_elastic["host"]}',
                        'ELASTICSEARCH_USERNAME': config_elastic['user'],
                        'ELASTICSEARCH_PASSWORD': config_elastic['pass']
                    },
                    mounts=self.mounts['kibana'],
                    **more_params
                )
            )

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['kibana'],
                    ipv4_address=config['virtual_ip']
                )

    def start_nodeos(self, space_monitor=True):
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

            if not self.is_nodeos_relaunch:
                if 'snapshot' in config:
                    env['NODEOS_SNAPSHOT'] = config['snapshot']

                elif 'genesis' in config:
                    env['NODEOS_GENESIS_JSON'] = f'/root/genesis/{config["genesis"]}.json'

            self.logger.info(f'is relaunch: {self.is_nodeos_relaunch}')

            nodeos_api_port = int(config['ini']['http_addr'].split(':')[1])
            history_port = int(config['ini']['history_endpoint'].split(':')[1])

            more_params = {}
            if sys.platform == 'darwin':
                more_params['ports'] = {
                    f'{nodeos_api_port}/tcp': nodeos_api_port,
                    f'{history_port}/tcp': history_port
                }
                more_params['mem_limit'] = '6g'

            # generate nodeos command
            nodeos_cmd = [
                'nodeos',
                '-e',
                '-p', 'eosio',
                '--config=/root/config.ini',
                f'--data-dir={config["data_dir_guest"]}',
                '--disable-replay-opts',
                '--logconf=/root/logging.json'
            ]

            if not self.is_nodeos_relaunch:
                if 'snapshot' in config:
                    nodeos_cmd += [f'--snapshot={config["snapshot"]}']

                elif 'genesis' in config:
                    nodeos_cmd += [f'--genesis-json=/root/genesis/{config["genesis"]}.json']


            if not space_monitor:
                nodeos_cmd += ['--resource-monitor-not-shutdown-on-threshold-exceeded']

            nodeos_cmd += ['>>', config['log_path'], '2>&1']
            nodeos_cmd_str = ' '.join(nodeos_cmd)

            cmd = ['/bin/bash', '-c', nodeos_cmd_str]

            self.logger.info(f'running nodeos container with command:')
            self.logger.info(' '.join(cmd))

            # open container
            self.containers['nodeos'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.chain_name}',
                    command=cmd,
                    environment=env,
                    mounts=self.mounts['nodeos'],
                    **more_params
                )
            )

            exec_id, exec_stream = docker_open_process(
                self.client, self.containers['nodeos'],
                ['/bin/bash', '-c',
                    'while true; do logrotate /root/logrotate.conf; sleep 60; done'])

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['nodeos'],
                    ipv4_address=config['virtual_ip']
                )

            cleos_url = f'http://127.0.0.1:{nodeos_api_port}'

            # setup cleos wrapper
            cleos = CLEOSEVM(
                self.client,
                self.containers['nodeos'],
                logger=self.logger,
                url=cleos_url,
                chain_id=self.config['telos-evm-rpc']['chain_id'])

            self.cleos = cleos

            if self.is_local:
                # await for nodeos to produce a block
                cleos.wait_blocks(4)

                self.is_fresh = 'Starting fresh blockchain state using provided genesis state' in output

                if self.is_fresh:
                    cleos.start_keosd(
                        '-c',
                        '/root/keosd_config.ini')

                    cleos.setup_wallet(self.producer_key)

                    try:
                        cleos.boot_sequence(
                            sys_contracts_mount='/opt/eosio/bin/contracts',
                            verify_hash=False)

                        cleos.deploy_evm()

                        evm_deploy_block = cleos.evm_deploy_info['processed']['block_num']

                        self.config['telosevm-translator']['start_block'] = evm_deploy_block
                        self.config['telosevm-translator']['deploy_block'] = evm_deploy_block

                        # save evm deploy info for future runs
                        with open(self.root_pwd / 'tevmc.json', 'w+') as uni_conf:
                            uni_conf.write(json.dumps(self.config, indent=4))

                    except AssertionError:
                        for msg in self.stream_logs(self.containers['nodeos']):
                            self.logger.critical(msg.rstrip())
                        sys.exit(1)

            else:
                cleos.wait_received(from_file=config['log_path'])

            genesis_block = self.config['telosevm-translator']['start_block'] - 1
            self.logger.info(f'nodeos has started, waiting until blocks.log contains evm genesis block number {genesis_block}')
            cleos.wait_blocks(
                genesis_block - cleos.get_info()['head_block_num'], sleep_time=10)

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
        delta = remote_head_block - self.cleos.get_info()['head_block_num']

        for line in self.stream_logs(self.containers['telosevm-translator']):
            if '] pushed, at ' in line:
                m = re.findall(r'(?<=: \[)(.*?)(?=\|)', line)
                if len(m) == 1 and m[0] != 'NaN':
                    last_indexed_block = int(m[0].replace(',', ''))

                    delta = remote_head_block - last_indexed_block

            self.logger.info(f'waiting on indexer... delta: {delta}')

            if delta < 100:
                break

            now = time.time()
            if now - last_update_time > 3600:
                remote_head_block = self._get_head_block()
                last_update_time = now

    def setup_index_patterns(self, patterns: List[str]):
        kibana_port = self.config['kibana']['port']

        if sys.platform == 'darwin':
            kibana_host = self.config['kibana']['virtual_ip']

        else:
            kibana_host = '127.0.0.1'

        for pattern_title in patterns:
            self.logger.info(
                f'registering index pattern \'{pattern_title}\'')
            while True:
                try:
                    resp = requests.post(
                        f'http://{kibana_host}:{kibana_port}'
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

            rpc_docker_dir = self.docker_wd / self.config['telos-evm-rpc']['docker_path']
            data_dir = rpc_docker_dir / self.config['telos-evm-rpc']['logs_dir']
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
                    f'{config["tag"]}-{self.chain_name}',
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

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['beats'],
                    ipv4_address=config['virtual_ip']
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

    def start_telosevm_translator(self):
        with self.must_keep_running('telosevm-translator'):
            config = self.config['telosevm-translator']
            config_elastic = self.config['elasticsearch']
            config_nodeos = self.config['nodeos']
            config_rpc = self.config['telos-evm-rpc']

            if sys.platform == 'darwin':
                nodeos_host = self.config['nodeos']['virtual_ip']

            else:
                nodeos_host = '127.0.0.1'

            nodeos_api_port = config_nodeos['ini']['http_addr'].split(':')[1]
            nodeos_ship_port = config_nodeos['ini']['history_endpoint'].split(':')[1]
            endpoint = f'http://{nodeos_host}:{nodeos_api_port}'

            if 'testnet' in self.chain_name:
                remote_endpoint = 'https://testnet.telos.net'
            elif 'mainnet' in self.chain_name:
                remote_endpoint = 'https://mainnet.telos.net'
            else:
                remote_endpoint = endpoint

            ws_endpoint = f'ws://{nodeos_host}:{nodeos_ship_port}'

            bc_host = config_rpc['indexer_websocket_host']
            bc_port = config_rpc['indexer_websocket_port']

            more_params = {}
            if sys.platform == 'darwin':
                more_params['ports'] = {f'{bc_port}/tcp': bc_port}

            self.containers['telosevm-translator'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.chain_name}',
                    environment={
                        'CHAIN_NAME': self.chain_name,
                        'CHAIN_ID': config_rpc['chain_id'],
                        'ELASTIC_USERNAME': config_elastic['user'],
                        'ELASTIC_PASSWORD': config_elastic['pass'],
                        'ELASTIC_NODE': f'http://{config_elastic["host"]}',
                        'ELASTIC_DUMP_SIZE': config['elastic_dump_size'],
                        'TELOS_ENDPOINT': endpoint,
                        'TELOS_REMOTE_ENDPOINT': remote_endpoint,
                        'TELOS_WS_ENDPOINT': ws_endpoint,
                        'INDEXER_START_BLOCK': config['start_block'],
                        'INDEXER_STOP_BLOCK': config['stop_block'],
                        'EVM_DEPLOY_BLOCK': config['deploy_block'],
                        'EVM_PREV_HASH': config['prev_hash'],
                        'BROADCAST_HOST': bc_host,
                        'BROADCAST_PORT': bc_port
                    },
                    **more_params
                )
            )

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['telosevm-translator'],
                    ipv4_address=config['virtual_ip']
                )

            for msg in self.stream_logs(self.containers['telosevm-translator']):
                self.logger.info(msg.rstrip())
                if 'drained' in msg:
                    break

    def setup_rpc_log_mount(self):
        docker_dir = self.docker_wd / self.config['telos-evm-rpc']['docker_path']
        logs_dir = docker_dir / self.config['telos-evm-rpc']['logs_dir']
        logs_dir.mkdir(parents=True, exist_ok=True)

        self.mounts['telos-evm-rpc'] = [
            Mount('/root/.pm2/logs', str(logs_dir.resolve()), 'bind')
        ]

    def start_evm_rpc(self):
        with self.must_keep_running('telos-evm-rpc'):
            config = self.config['telos-evm-rpc']

            api_port = config['api_port']
            rpc_port = config['rpc_websocket_port']

            more_params = {}
            if sys.platform == 'darwin':
                more_params['ports'] = {
                    f'{api_port}/tcp': api_port,
                    f'{rpc_port}/tcp': rpc_port
                }

            self.containers['telos-evm-rpc'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.chain_name}',
                    mounts=self.mounts['telos-evm-rpc'],
                    **more_params
                )
            )

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['telos-evm-rpc'],
                    ipv4_address=config['virtual_ip']
                )

            for msg in self.stream_logs(self.containers['telos-evm-rpc']):
                self.logger.info(msg.rstrip())
                if 'Telos EVM RPC started!!!' in msg:
                    break

    def open_rpc_websocket(self):
        rpc_ws_host = self.config['telos-evm-rpc']['rpc_websocket_host']
        rpc_ws_port = self.config['telos-evm-rpc']['rpc_websocket_port']

        connected = False
        for i in range(3):
            try:
                ws = create_connection(
                    f'ws://{rpc_ws_host}:{rpc_ws_port}/evm')
                connected = True
                break

            except ConnectionRefusedError:
                time.sleep(5)

        assert connected
        return ws

    def darwin_network_setup(self):
        try:
            self._vnet = self.client.networks.get(self.chain_name)

        except docker.errors.NotFound:
            ipam_pool = docker.types.IPAMPool(
                subnet='192.168.123.0/24',
                gateway='192.168.123.254'
            )
            ipam_config = docker.types.IPAMConfig(
                pool_configs=[ipam_pool]
            )

            self._vnet = self.client.networks.create(
                self.chain_name, 'bridge', ipam=ipam_config
            )

    def start(self):

        if sys.platform == 'darwin':
            self.darwin_network_setup()

        if 'redis' in self.services:
            self.start_redis()

        if 'elastic' in self.services:
            self.start_elasticsearch()

        if 'kibana' in self.services:
            self.start_kibana()

        if 'nodeos' in self.services:
            self.start_nodeos()

        if 'indexer' in self.services:
            self.start_telosevm_translator()

            if not self.is_local and self.wait:
                self.await_full_index()


        if 'kibana' in self.services:
            idx_version = self.config['telos-evm-rpc']['elasitc_index_version']
            self.setup_index_patterns([
                f'{self.chain_name}-action-{idx_version}-*',
                f'{self.chain_name}-delta-{idx_version}-*',
                'filebeat-*'
            ])


        if 'rpc' in self.services:
            self.setup_rpc_log_mount()
            self.start_evm_rpc()

        else:
            if self.wait:
                self.logger.warning('--wait passed but no indexer launched, ignoring...')

        if 'beats' in self.services:
            self.start_beats()

        if self.is_local and self.is_fresh and 'nodeos' in self.services:
            self.cleos.create_test_evm_account()

    def stop(self):
        if 'nodeos' in self.services:
            self.cleos.stop_nodeos(
                from_file=self.config['nodeos']['log_path'])

            self.is_nodeos_relaunch = True

        if 'elastic' in self.services:
            self.stop_elasticsearch()
            self.is_elastic_relaunch = True

        self.exit_stack.pop_all().close()

        if self.nodeos_logproc:
            self.nodeos_logproc.kill()
            self.nodeos_logfile.close()


    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
