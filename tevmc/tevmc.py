#!/usr/bin/env python3

import re
import os
import sys
import time
import signal
import logging
import subprocess

from copy import deepcopy
from hashlib import sha1
from pathlib import Path
from websocket import create_connection
from contextlib import contextmanager, ExitStack

import docker
import requests
import simplejson

from web3 import Web3
from flask import Flask
from docker.types import LogConfig, Mount
from docker.errors import NotFound, APIError
from requests.auth import HTTPBasicAuth
from leap.cleos import CLEOS
from leap.sugar import download_latest_snapshot
from tevmc.cmdline.build import build_service, perform_config_build, service_alias_to_fullname

from tevmc.routes import add_routes

from .config import *
from .utils import *
from .cleos_evm import CLEOSEVM


class TEVMCException(BaseException):
    ...


class TEVMController:

    def __init__(
        self,
        config: dict[str, dict],
        logger = None,
        log_level: str = 'info',
        root_pwd: Path | None = None,
        wait: bool = False,
        services: list[str] = [
            'redis',
            'elastic',
            'kibana',
            'nodeos',
            'indexer',
            'rpc',
        ],
        from_latest: bool = False,
        is_producer: bool = True,
        skip_init: bool = False,
        additional_nodeos_params: list[str] = [],
        testing: bool = False
    ):
        self.pid = os.getpid()
        self.config = config
        self.client = docker.from_env()
        self.exit_stack = ExitStack()
        self.wait = wait
        self.services = services
        self.testing = testing
        self.nodeos_logfile = None
        self.nodeos_logproc = None
        self.additional_nodeos_params = additional_nodeos_params

        if not root_pwd:
            self.root_pwd = Path().resolve()
        else:
            self.root_pwd = root_pwd

        self.main_logs_dir = self.root_pwd / 'logs'
        self.main_logs_dir.mkdir(parents=True, exist_ok=True)

        self.docker_wd = self.root_pwd / 'docker'

        self.is_producer = is_producer
        self.skip_init = skip_init

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

        self.chain_type = 'local'
        if 'testnet' in self.chain_name:
            self.chain_type = 'testnet'
        elif 'mainnet' in self.chain_name:
            self.chain_type = 'mainnet'

        self.cleos: CLEOSEVM = None

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
                self._dump_config()


        self.containers = {}
        self.mounts = {}

        self.api = Flask(f'tevmc-{os.getpid()}')

    def _dump_config(self):
        with open(self.root_pwd / 'tevmc.json', 'w+') as uni_conf:
            uni_conf.write(json.dumps(self.config, indent=4))

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
                    container.kill(signal='SIGTERM')
                    for i in range(3):
                        container.stop()

            except APIError as e:
                ...

            self.logger.info('stopped.')

            # self.logger.info(f'removing container \"{name}\"')
            # try:
            #     if container:
            #         for i in range(3):
            #             container.remove()
            # except docker.errors.APIError as e:
            #     ...

            # self.logger.info('removed.')


    def stream_logs(self, container, timeout=30.0, num=100, from_latest=False):
        if container is None:
            self.logger.critical("container is None")
            raise StopIteration

        elif container in ['nodeos', 'telosevm-translator', 'telos-evm-rpc']:
            for line in self._stream_logs_from_main_dir(
                container, num, timeout=int(timeout)):
                yield line

        else:
            for chunk in docker_stream_logs(
                self.containers[container],
                lines=num,
                timeout=timeout,
                from_latest=from_latest
            ):
                yield chunk

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

            for msg in self.stream_logs('redis'):
                self.logger.info(msg.rstrip())
                if 'Ready to accept connections' in msg:
                    break

    def start_elasticsearch(self):
        with self.must_keep_running('elasticsearch'):
            config = self.config['elasticsearch']
            docker_dir = self.docker_wd / config['docker_path']

            data_dir = docker_dir / config['data_dir']
            data_dir.mkdir(parents=True, exist_ok=True)

            self.mounts['elasticsearch'] = [
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
                        'xpack.security.enabled': 'false',
                        'ES_JAVA_OPTS': '-Xms2g -Xmx2g',
                        'ES_NETWORK_HOST': '0.0.0.0'
                    },
                    user='root',
                    mounts=self.mounts['elasticsearch'],
                    **more_params
                )
            )

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['elasticsearch'],
                    ipv4_address=config['virtual_ip']
                )

            for msg in self.stream_logs('elasticsearch'):
                self.logger.info(msg.rstrip())
                if ' indices into cluster_state' in msg:
                    break

    def stop_elasticsearch(self):
        self.containers['elasticsearch'].kill(signal.SIGTERM)

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

    def _stop_nodeos(self):
        # remove container if exists
        cntr = self.containers.get('nodeos', None)
        if cntr is not None:
            try:
                cntr.exec_run('pkill -f nodeos')
                cntr.wait(timeout=120)
                cntr.kill(signal='SIGTERM')
                cntr.wait(timeout=20)

            except NotFound:
                ...

            except APIError:
                ...

    def start_nodeos(
        self,
        space_monitor=True,
        do_init=True
    ):
        """Start eosio_nodeos container.

        - Initialize CLEOS wrapper and setup keosd & wallet.
        - Launch nodeos with config.ini
        - Wait for nodeos 
                    to produce blocks
        - Create evm accounts and deploy contract
        """
        self._stop_nodeos()

        config = self.config['nodeos']
        docker_dir = self.docker_wd / config['docker_path']

        data_dir_guest = config['data_dir_guest']
        data_dir_host = docker_dir / config['data_dir_host']

        conf_dir = docker_dir / config['conf_dir']
        contracts_dir = docker_dir / config['contracts_dir']
        contracts_dir = contracts_dir.resolve(strict=True)

        data_dir_host.mkdir(parents=True, exist_ok=True)

        self.mounts['nodeos'] = [
            Mount('/root', str(conf_dir.resolve()), 'bind'),
            Mount('/opt/eosio/bin/contracts', str(contracts_dir.resolve()), 'bind'),
            Mount(data_dir_guest, str(data_dir_host.resolve()), 'bind'),
            Mount('/logs', str(self.main_logs_dir.resolve()), 'bind')
        ]

        if 'mounts' in config:
            self.mounts['nodeos'] += [
                Mount(m['target'], m['source'], 'bind') for m in config['mounts']]

        if self.testing:
            self.mounts['nodeos'] += [
                Mount('/opt/eosio/bin/testcontracts', str(Path('tests/contracts').resolve()), 'bind')]

        env = {
            'NODEOS_DATA_DIR': config['data_dir_guest'],
            'NODEOS_CONFIG': f'/root/config.ini',
            'NODEOS_LOG_PATH': '/logs/nodeos.log',
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
            config['nodeos_bin'],
            '--config=/root/config.ini',
            f'--data-dir={config["data_dir_guest"]}',
            '--logconf=/root/logging.json'
        ]

        if 'eosio::state_history_plugin' in config['ini']['plugins']:
            nodeos_cmd += ['--disable-replay-opts']

        if (not self.is_nodeos_relaunch or
            '--replay-blockchain' in self.additional_nodeos_params):
            if 'snapshot' in config:
                nodeos_cmd += [f'--snapshot={config["snapshot"]}']

            elif 'genesis' in config:
                nodeos_cmd += [
                    f'--genesis-json=/root/genesis/{config["genesis"]}.json'
                ]

        if not space_monitor:
            nodeos_cmd += ['--resource-monitor-not-shutdown-on-threshold-exceeded']

        if self.is_producer:
            nodeos_cmd += ['-e', '-p', 'eosio']

        if config['ini'].get('subst_admin_apis', False):
            nodeos_cmd += ['--subst-admin-apis']

        override_tx_time = config.get('override_tx_time', 0)
        if override_tx_time:
            nodeos_cmd += [f'--override-max-tx-time={override_tx_time}']

        nodeos_cmd += self.additional_nodeos_params

        nodeos_cmd += ['>>', '/logs/nodeos.log', '2>&1']
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
        self.containers['nodeos'].reload()

        if not do_init:
            return

        with self.must_keep_running('nodeos'):
            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['nodeos'],
                    ipv4_address=config['virtual_ip']
                )

            cleos_url = f'http://127.0.0.1:{nodeos_api_port}'

            cleos_evm_url = f'http://127.0.0.1:{self.config["telos-evm-rpc"]["api_port"]}/evm'


            # maybe setup cleos wrapper, if its already setup indicates an inplace restart and cleos
            # data should be mantained
            if not isinstance(self.cleos, CLEOSEVM):
                self.cleos = CLEOSEVM(
                    endpoint=cleos_url,
                    logger=self.logger,
                    evm_url=cleos_evm_url,
                    chain_id=self.config['telos-evm-rpc']['chain_id'])

                if 'sig_provider' in config['ini']:
                    key = config['ini']['sig_provider'].split('=KEY:')[-1]
                    self.cleos.import_key('eosio', key)

                self.cleos.load_abi_file('eosio', contracts_dir / 'eosio.system/eosio.system.abi')
                self.cleos.load_abi_file('eosio.evm', contracts_dir / 'eosio.evm' / self.chain_type / 'regular/regular.abi')
                self.cleos.load_abi_file('eosio.token', contracts_dir / 'eosio.token/eosio.token.abi')

            if self.is_local:

                if self.skip_init:
                    return

                output = ''
                for msg in self.stream_logs('nodeos', timeout=60*10, from_latest=True):
                    output += msg
                    if 'Produced' in msg:
                        break

                # await for nodeos to produce a block
                self.cleos.wait_blocks(4)

                self.is_fresh = (
                    'No existing chain state or fork database. '
                    'Initializing fresh blockchain state and resetting fork database.' in output
                )

                if self.is_fresh:
                    self.cleos.import_key('eosio', self.producer_key)

                    try:
                        self.cleos.boot_sequence(
                            contracts=contracts_dir, remote_node=CLEOS('https://testnet.telos.net'))

                        self.cleos.deploy_evm(contracts_dir / 'eosio.evm' / self.chain_type / self.config['nodeos']['eosio.evm'])

                    except AssertionError:
                        for msg in self.stream_logs('nodeos'):
                            self.logger.critical(msg.rstrip())
                        sys.exit(1)

            else:
                if ('--replay-blockchain' not in self.additional_nodeos_params and
                    len(config['ini']['peers']) > 0):
                    for msg in self.stream_logs('nodeos', timeout=60*10, from_latest=True):
                        if 'Received' in msg:
                            break

            if not self.skip_init:
                # wait until nodeos apis are up
                for i in range(60):
                    try:
                        self.nodeos_init_info = self.cleos.get_info()
                        current_chain_id = self.nodeos_init_info['chain_id']
                        config_chain_id = self.config['nodeos']['chain_id']

                        if config_chain_id == 'override':
                            self.config['nodeos']['chain_id'] = current_chain_id
                            self.build(templates_only=True)

                        else:
                            if config_chain_id != current_chain_id:
                                raise ValueError(
                                    f'chain id returned ({current_chain_id}) '
                                    f'from nodeos differs from one on config ({config_chain_id})')

                        break

                    except requests.exceptions.ConnectionError:
                        self.logger.warning('connection error trying to get chain info...')
                        time.sleep(1)

                translator_start_block = int(self.config['telosevm-translator']['start_block']) - 1
                self.logger.info(
                    'nodeos has started, waiting until blocks.log '
                    f'contains block number {translator_start_block}'
                )
                self.cleos.wait_block(
                    translator_start_block, progress=True, interval=5)

    def restart_nodeos(self):
        self._stop_nodeos()

        self.is_nodeos_relaunch = True

        time.sleep(4)

        self.start_nodeos()

    def _stream_logs_from_main_dir(
        self,
        service: str,
        lines: int = 100,
        timeout: int = 60
    ):
        log_path = self.main_logs_dir
        log_path /= f'{service}.log'
        log_path = log_path.resolve()

        for _ in range(3):
            if not log_path.is_file():
                time.sleep(1)

            else:
                break

        process = subprocess.Popen(
            ['bash', '-c',
                f'timeout {timeout}s tail -n {lines} -f {log_path}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        for line in iter(process.stdout.readline, b''):
            msg = line.decode('utf-8')
            if 'clear_expired_input_' in msg:
                continue
            yield msg
            self.logger.info(msg.rstrip())

        process.stdout.close()
        process.wait()

        if process.returncode != 0:
            raise ValueError(
                f'tail returned {process.returncode}\n'
                f'{process.stderr.read().decode("utf-8")}')

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

        for line in self.stream_logs('telosevm-translator'):
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

    def setup_index_patterns(self, patterns: list[str]):
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
            tevmi_conf_dir = self.docker_wd / config['docker_path'] / config['conf_dir']

            self.mounts['telosevm-translator'] = [
                Mount('/logs', str(self.main_logs_dir.resolve()), 'bind'),
                Mount('/root/indexer/config', str(tevmi_conf_dir.resolve()), 'bind')
            ]

            more_params = {}
            if sys.platform == 'darwin':
                more_params['ports'] = {f'{bc_port}/tcp': bc_port}

            self.containers['telosevm-translator'] = self.exit_stack.enter_context(
                self.open_container(
                    f'{config["name"]}-{self.pid}-{self.chain_name}',
                    f'{config["tag"]}-{self.chain_name}',
                    mounts=self.mounts['telosevm-translator'],
                    **more_params
                )
            )

            if sys.platform == 'darwin':
                self._vnet.connect(
                    self.containers['telosevm-translator'],
                    ipv4_address=config['virtual_ip']
                )

            for msg in self.stream_logs('telosevm-translator', timeout=60*10):
                if 'drained' in msg:
                    break

    def restart_translator(self):
        if 'telosevm-translator' in self.containers:
            container = self.containers['telosevm-translator']
            try:
                container.reload()

                if container.status == 'running':
                    container.stop()
                    container.remove()

            except docker.errors.NotFound:
                ...

        self.start_telosevm_translator()


    def start_evm_rpc(self):
        with self.must_keep_running('telos-evm-rpc'):
            config = self.config['telos-evm-rpc']
            docker_dir = self.docker_wd / config['docker_path']
            conf_dir = docker_dir / config['conf_dir']

            self.mounts['telos-evm-rpc'] = [
                Mount('/logs', str(self.main_logs_dir.resolve()), 'bind'),
                Mount('/root/target', str(conf_dir.resolve()), 'bind')
            ]

            more_params = {}
            if sys.platform == 'darwin':
                api_port = config['api_port']
                rpc_port = config['rpc_websocket_port']
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

            for msg in self.stream_logs('telos-evm-rpc'):
                self.logger.info(msg.rstrip())
                if 'Telos EVM RPC started!!!' in msg:
                    break

    def restart_rpc(self):
        if 'telos-evm-rpc' in self.containers:
            container = self.containers['telos-evm-rpc']
            try:
                container.reload()

                if container.status == 'running':
                    container.stop()
                    container.remove()

            except docker.errors.NotFound:
                ...

        self.start_evm_rpc()

    def open_rpc_websocket(self):
        rpc_ws_host = '127.0.0.1'  # self.config['telos-evm-rpc']['rpc_websocket_host']
        rpc_ws_port = self.config['telos-evm-rpc']['rpc_websocket_port']

        rpc_endpoint = f'ws://{rpc_ws_host}:{rpc_ws_port}/evm'
        self.logger.info(f'connecting to {rpc_endpoint}')

        connected = False
        for i in range(3):
            try:
                ws = create_connection(rpc_endpoint)
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

    def build(
        self,
        force_conf_rebuild: bool = False,
        templates_only: bool = False,
        use_cache: bool = True
    ):
        self.logger.info('starting build...')
        rebuild_conf = False
        prev_hash = None
        cfg = deepcopy(self.config.copy())
        if 'metadata' in cfg:
            cfg.pop('metadata', None)
            prev_hash = self.config['metadata']['phash']
            self.logger.info(f'previous hash: {prev_hash}')

        hasher = sha1(json.dumps(cfg, sort_keys=True).encode('utf-8'))
        curr_hash = hasher.hexdigest()

        self.logger.info(f'current hash: {curr_hash}')

        rebuild_conf = (prev_hash != curr_hash) or force_conf_rebuild

        if rebuild_conf:
            cfg['metadata'] = {}
            cfg['metadata']['phash'] = curr_hash

            with open(self.root_pwd / 'tevmc.json', 'w+') as uni_conf:
                uni_conf.write(json.dumps(cfg, indent=4))

            self.logger.info('Rebuilding config files...')
            perform_config_build(self.root_pwd, cfg)
            self.logger.info('done.')

            self.config = cfg

        if templates_only:
            return

        # docker build
        for service in self.services:
            name = service_alias_to_fullname(service)
            conf = self.config[name]
            if 'docker_path' in conf:
                build_service(
                    self.root_pwd, name,
                    self.config, self.logger,
                    nocache=not use_cache)

    def start(self):

        self.build()

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
            self.start_evm_rpc()

        else:
            if self.wait:
                self.logger.warning('--wait passed but no indexer launched, ignoring...')

        if 'beats' in self.services:
            self.start_beats()

        if (self.is_local and
            self.is_fresh and
            not self.skip_init and
            'nodeos' in self.services):
            self.cleos.create_test_evm_account()

    def serve_api(self):
        add_routes(self)
        self.api.run(port=self.config['daemon']['port'])

    def stop(self):
        if 'nodeos' in self.services:
            self._stop_nodeos()
            self.is_nodeos_relaunch = True

        if 'elastic' in self.services:
            self.stop_elasticsearch()
            self.is_elastic_relaunch = True

        if self.nodeos_logproc:
            self.nodeos_logproc.kill()
            self.nodeos_logfile.close()

        self.exit_stack.pop_all().close()

        pid_path = self.root_pwd / 'tevmc.pid'
        if pid_path.is_file():
            pid_path.unlink(missing_ok=True)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
