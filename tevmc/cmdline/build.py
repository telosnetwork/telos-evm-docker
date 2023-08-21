#!/usr/bin/env python3

import os
import sys
import json

import click
import docker

from typing import Dict, Any
from hashlib import sha1
from pathlib import Path
from datetime import datetime

from .cli import cli, get_docker_client
from .init import load_config_templates, load_docker_templates
from ..config import *


DEFAULT_SERVICES = ['redis', 'elastic', 'kibana', 'nodeos', 'indexer', 'rpc', 'beats']
TEST_SERVICES = ['redis', 'elastic', 'kibana', 'nodeos', 'indexer', 'rpc']


class TEVMCBuildException(Exception):
    ...


def perform_config_build(target_dir, config):
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    docker_dir = target_dir / 'docker'
    docker_dir.mkdir(exist_ok=True)

    # config build
    timestamp = {'timestamp': str(datetime.now())}
    templates = load_config_templates()
    docker_templates = load_docker_templates()

    def flatten(master_key, _dict, fkey=None) -> Dict:
        ndict = {}
        if not fkey:
            fkey = master_key

        for key, val in _dict[fkey].items():
            ndict[f'{master_key}_{key}'] = val

        return ndict

    def jsonize(_dict: Dict[str, Any], **kwargs) -> Dict[str, str]:
        ndict = {}
        for key, val in _dict.items():
            ndict[key] = json.dumps(val, **kwargs)

        return ndict

    def write_config_file(
        fname: str,
        dir_target: str,
        subst: Dict[str, Any]
    ):
        with open(docker_dir / Path(dir_target) / fname, 'w+') as target_file:
            target_file.write(
                templates[fname].substitute(**subst))

    def write_docker_template(file, subst: Dict[str, Any]):
        with open(docker_dir / file, 'w+') as conf_file:
            conf_file.write(
                docker_templates[file].substitute(**subst))


    # redis
    redis_conf = config['redis']

    redis_dir = redis_conf['docker_path']
    redis_build_dir = redis_dir + '/' + 'build'
    redis_conf_dir = redis_dir + '/' +  redis_conf['conf_dir']

    subst = flatten('redis', config)
    write_docker_template(f'{redis_build_dir}/Dockerfile', subst)
    write_docker_template(f'{redis_conf_dir}/redis.conf', subst)

    # elasticsearch
    elastic_conf = config['elasticsearch']

    elastic_dir = elastic_conf['docker_path']
    elastic_build_dir = elastic_dir + '/' + 'build'
    elastic_data_dir = elastic_dir + '/' + elastic_conf['data_dir']
    subst = {
        'elasticsearch_port': config['elasticsearch']['host'].split(':')[-1]
    }
    write_docker_template(f'{elastic_build_dir}/Dockerfile', subst)
    write_docker_template(f'{elastic_build_dir}/elasticsearch.yml', subst)

    host_dir = (docker_dir / elastic_data_dir)
    host_dir.mkdir(parents=True, exist_ok=True)

    os.chown(host_dir, uid=os.getuid(), gid=os.getgid())

    # kibana
    kibana_conf = config['kibana']

    kibana_dir = kibana_conf['docker_path']
    kibana_build_dir = kibana_dir + '/' + 'build'
    kibana_conf_dir  = kibana_dir + '/' + kibana_conf['conf_dir']

    subst = flatten('kibana', config)
    write_docker_template(f'{kibana_build_dir}/Dockerfile', subst)
    write_docker_template(f'{kibana_conf_dir}/kibana.yml', subst)

    # nodeos
    chain_name = config['telos-evm-rpc']['elastic_prefix']
    nodeos_conf = config['nodeos']
    ini_conf = nodeos_conf['ini']

    nodeos_dir = nodeos_conf['docker_path']
    nodeos_conf_dir = nodeos_dir + '/' + nodeos_conf['conf_dir']
    nodeos_build_dir = nodeos_dir + '/' + 'build'
    nodeos_http_port = int(ini_conf['http_addr'].split(':')[-1])

    subst = {
        'nodeos_port': nodeos_http_port,
        'nodeos_history_port': ini_conf['history_endpoint'].split(':')[-1]
    }
    write_docker_template(f'{nodeos_build_dir}/Dockerfile', subst)

    # logrotate.conf
    write_config_file(
        'logrotate.conf',
        nodeos_conf_dir,
        {'nodeos_log_path': get_config('nodeos.log_path', config)})

    # nodeos.config.ini
    subst = {}
    subst.update(get_config('nodeos.ini', config))
    subst.update(timestamp)

    # normalize bools
    for key, val in subst.items():
        if isinstance(val, bool):
            subst[key] = str(val).lower()

    conf_str = templates['nodeos.config.ini'].substitute(**subst) + '\n'

    if 'local' in chain_name:
        conf_str += templates['nodeos.local.config.ini'].substitute(**subst) + '\n'

    for plugin in subst['plugins']:
        conf_str += f'plugin = {plugin}\n'

    if 'subst' in subst:
        conf_str += f'plugin = eosio::subst_plugin\n'
        conf_str += '\n'
        sinfo = subst['subst']
        if isinstance(sinfo, str):
            conf_str += f'subst-manifest = {sinfo}'

        elif isinstance(sinfo, dict):
            for skey, val in sinfo.items():
                conf_str += f'subst-by-name = {skey}:{val}'

    conf_str += '\n'

    for peer in subst['peers']:
        conf_str += f'p2p-peer-address = {peer}\n'

    with open(docker_dir / nodeos_conf_dir / 'config.ini', 'w+') as target_file:
        target_file.write(conf_str)

    # beats
    beats_conf = config['beats']
    beats_dir = docker_dir / beats_conf['docker_path']

    # telosevm-translator
    tevmi_conf = config['telosevm-translator']
    tevmi_dir = tevmi_conf['docker_path']
    tevmi_build_dir = tevmi_dir + '/' + 'build'

    subst = {
        'broadcast_port':
            config['telos-evm-rpc']['indexer_websocket_port'],
    }
    write_docker_template(f'{tevmi_build_dir}/Dockerfile', subst)

    # telos-evm-rpc
    rpc_conf = config['telos-evm-rpc']

    rpc_dir = rpc_conf['docker_path']
    rpc_build_dir = rpc_dir + '/' + 'build'
    subst = jsonize({
        'rpc_chain_id': rpc_conf['chain_id'],
        'rpc_debug': rpc_conf['debug'],
        'rpc_host': rpc_conf['api_host'],
        'rpc_api': rpc_conf['api_port'],
        'rpc_nodeos_read': f'http://127.0.0.1:{nodeos_http_port}',
        'rpc_signer_account': rpc_conf['signer_account'],
        'rpc_signer_permission': rpc_conf['signer_permission'],
        'rpc_signer_key': rpc_conf['signer_key'],
        'rpc_contracts': rpc_conf['contracts'],
        'rpc_indexer_websocket_host': rpc_conf['indexer_websocket_host'],
        'rpc_indexer_websocket_port': rpc_conf['indexer_websocket_port'],
        'rpc_indexer_websocket_uri': rpc_conf['indexer_websocket_uri'],
        'rpc_websocket_host': rpc_conf['rpc_websocket_host'],
        'rpc_websocket_port': rpc_conf['rpc_websocket_port'],
        'redis_host': config['redis']['host'],
        'redis_port': config['redis']['port'],
        'rpc_elastic_node': f'http://{elastic_conf["host"]}',
        'elasticsearch_user': elastic_conf['user'],
        'elasticsearch_pass': elastic_conf['pass'],
        'elasticsearch_prefix': rpc_conf['elastic_prefix'],
        'elasticsearch_index_version': rpc_conf['elasitc_index_version']
    })
    write_docker_template(f'{rpc_build_dir}/config.json', subst)
    subst = {
        'api_port':
            config['telos-evm-rpc']['api_port'],
        'ws_port':
            config['telos-evm-rpc']['indexer_websocket_port']
    }
    write_docker_template(f'{rpc_build_dir}/Dockerfile', subst)


def service_alias_to_fullname(alias: str):
    if alias in ['elastic', 'es']:
        return 'elasticsearch'

    if alias in ['indexer', 'translator', 'evm']:
        return 'telosevm-translator'

    if alias in ['api', 'rpc']:
        return 'telos-evm-rpc'

    return alias


def perform_docker_build(target_dir, config, logger, services):
    perform_config_build(target_dir, config)

    docker_dir = target_dir / 'docker'
    docker_dir.mkdir(exist_ok=True)

    # docker build
    client = get_docker_client()
    chain_name = config['telos-evm-rpc']['elastic_prefix']

    builds = []
    for service in services:
        fullname = service_alias_to_fullname(service)
        conf = config[fullname]
        if 'docker_path' in conf:
            builds.append({
                'tag': f'{conf["tag"]}-{chain_name}',
                'path': str(docker_dir / conf['docker_path'] / 'build')
            })

    for build_args in builds:
        stream = ''
        logger.info(f'building {build_args}...')

        for chunk in client.api.build(**build_args):
            update = None
            _str = chunk.decode('utf-8').rstrip()

            # sometimes several json packets are sent per chunk
            splt_str = _str.split('\n')

            for packet in splt_str:
                msg = json.loads(packet)
                status = msg.get('status', None)
                status = msg.get('stream', None)
                if status:
                    strp_status = status.rstrip()
                    stream += status

        try:
            client.images.get(build_args['tag'])

        except docker.errors.NotFound:
            msg_ex = (
                f'couldn\'t build container {build_args["tag"]} at '
                f'{build_args["path"]}')
            logger.critical(msg_ex)
            logger.critical(stream)
            raise TEVMCBuildException(msg_ex)

        logger.info('building complete.')


@cli.command()
@click.option(
    '--always-conf/--smart-conf', default=False,
    help='Force configuration files rebuild from templates.')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--full-build/--templates-only', default=True,
    help='Perform docker build or only setup files.')
def build(always_conf, target_dir, config, full_build):
    """Build in-repo docker containers.
    """
    config_fname = config
    try:
        config = load_config(target_dir, config)

    except FileNotFoundError:
        print('Config not found.')
        sys.exit(1)

    target_dir = Path(target_dir).resolve()

    rebuild_conf = False
    prev_hash = None
    cfg = config.copy()
    if 'metadata' in cfg:
        cfg.pop('metadata', None)
        prev_hash = config['metadata']['phash']
        print(f'Previous hash: {prev_hash}')

    hasher = sha1(json.dumps(cfg, sort_keys=True).encode('utf-8'))
    curr_hash = hasher.hexdigest()

    print(f'Current hash: {curr_hash}')

    rebuild_conf = (prev_hash != curr_hash) or always_conf

    if rebuild_conf:
        config['metadata'] = {}
        config['metadata']['phash'] = curr_hash

        with open(target_dir / config_fname, 'w+') as uni_conf:
            uni_conf.write(json.dumps(config, indent=4))

        print('Rebuilding config files...', end='', flush=True)
        perform_config_build(target_dir, config)
        print('done.')

    if not full_build:
        return

    # docker build
    for name, conf in config.items():
        if 'docker_path' in conf:
            build_service(target_dir, name, config)


def build_service(target_dir: Path, service_name: str, config: dict, **kwargs):
    docker_dir = target_dir / 'docker'
    docker_dir.mkdir(exist_ok=True)

    chain_name = config['telos-evm-rpc']['elastic_prefix']
    client = get_docker_client()

    if service_name not in config:
        service_name = service_alias_to_fullname(service_name)

    config = config[service_name]

    image_tag = f'{config["tag"]}-{chain_name}'
    build_path = str(docker_dir / config['docker_path'] / 'build')

    for chunk in client.api.build(
        tag=image_tag, path=build_path, **kwargs):
        _str = chunk.decode('utf-8').rstrip()

        # sometimes several json packets are sent per chunk
        splt_str = _str.split('\n')

        for packet in splt_str:
            msg = json.loads(packet)
            status = msg.get('status', None)
            status = msg.get('stream', None)

            if status:
                print(status, end='')

    try:
        client.images.get(image_tag)

    except docker.errors.NotFound:
        raise TEVMCBuildException(
            f'couldn\'t build container {image_tag} at '
            f'{build_path}')
