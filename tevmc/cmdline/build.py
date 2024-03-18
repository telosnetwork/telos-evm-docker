#!/usr/bin/env python3

from copy import deepcopy
import logging
import os
import json

import docker
from docker.types import Mount

from pathlib import Path
from datetime import datetime

from .cli import cli, get_docker_client
from .init import load_docker_templates
from ..config import *


DEFAULT_SERVICES = ['redis', 'elastic', 'kibana', 'nodeos', 'indexer', 'rpc']
TEST_SERVICES = ['redis', 'elastic', 'kibana', 'nodeos', 'indexer', 'rpc']


class TEVMCBuildException(Exception):
    ...


def patch_config(template_dict, current_dict):
    diffs = []
    new_dict = {}

    for key, value in template_dict.items():
        if key in current_dict:
            if isinstance(value, dict) and isinstance(current_dict[key], dict):
                new_dict[key], inner_diffs = patch_config(value, current_dict[key])
                diffs += inner_diffs
            else:
                new_dict[key] = current_dict[key]
        else:
            new_dict[key] = value
            diffs.append(f'Added: {key}={value}')

    final_dict = deepcopy(current_dict)
    keys_to_remove = set(current_dict.keys()) - set(template_dict.keys())

    for key in keys_to_remove:
        del final_dict[key]
        diffs.append(f'Removed: {key}')

    final_dict.update(new_dict)

    return final_dict, diffs


def perform_config_build(target_dir, config):
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    docker_dir = target_dir / 'docker'
    docker_dir.mkdir(exist_ok=True)

    # config build
    timestamp = {'timestamp': str(datetime.now())}
    docker_templates = load_docker_templates()

    def flatten(master_key, _dict, fkey=None) -> dict:
        ndict = {}
        if not fkey:
            fkey = master_key

        for key, val in _dict[fkey].items():
            ndict[f'{master_key}_{key}'] = val

        return ndict

    def jsonize(_dict: dict, **kwargs) -> dict[str, str]:
        ndict = {}
        for key, val in _dict.items():
            ndict[key] = json.dumps(val, **kwargs)

        return ndict

    def write_docker_template(file, subst: dict):
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

    client = docker.from_env()
    client.containers.run(
        'bash',
        f'bash -c \"chown -R {os.getuid()}:{os.getgid()} /root/target\"',
        remove=True,
        mounts=[Mount('/root/target', str(host_dir), 'bind')]
    )

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

    # nodeos.config.ini
    subst = {}
    subst.update(get_config('nodeos.ini', config))
    subst.update(timestamp)

    # normalize bools
    for key, val in subst.items():
        if isinstance(val, bool):
            subst[key] = str(val).lower()

    conf_str = docker_templates[f'{nodeos_conf_dir}/nodeos.config.ini'].substitute(**subst) + '\n'

    if 'local' in chain_name:
        conf_str += docker_templates[f'{nodeos_conf_dir}/nodeos.local.config.ini'].substitute(**subst) + '\n'

    for plugin in subst['plugins']:
        conf_str += f'plugin = {plugin}\n'

    if 'subst' in subst:
        conf_str += f'plugin = eosio::subst_plugin\n'
        conf_str += f'plugin = eosio::subst_api_plugin\n'
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

    # rpc config.json gen
    subst = jsonize({
        'rpc_chain_id': rpc_conf['chain_id'],
        'nodeos_chain_id': nodeos_conf['chain_id'],
        'evm_block_delta': tevmi_conf['evm_block_delta'],
        'rpc_debug': rpc_conf['debug'],
        'rpc_host': rpc_conf['api_host'],
        'rpc_api': rpc_conf['api_port'],
        'rpc_nodeos_write': f'http://127.0.0.1:{nodeos_http_port}',
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
        'elasticsearch_index_version': rpc_conf['elasitc_index_version'],
        'elasticsearch_docs_per_index': tevmi_conf['elastic_docs_per_index']
    })

    rpc_conf_dir =  f'{rpc_dir}/{rpc_conf["conf_dir"]}'
    (docker_dir / rpc_conf_dir).mkdir(exist_ok=True, parents=True)
    write_docker_template(f'{rpc_conf_dir}/config.json', subst)

    # rpc docker template
    rpc_build_dir = rpc_dir + '/' + 'build'

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


@cli.command()
def build():
    print(
        'no need to run \"tevmc build\" command anymore, has been incorporated'
        'into \"tevmc up\" command.')


def build_service(target_dir: Path, service_name: str, config: dict, logger = None, **kwargs):
    if not logger:
        logger = logging.getLogger(f'build-{service_name}')

    docker_dir = target_dir / 'docker'
    docker_dir.mkdir(exist_ok=True)

    chain_name = config['telos-evm-rpc']['elastic_prefix']
    client = get_docker_client()

    if service_name not in config:
        service_name = service_alias_to_fullname(service_name)

    config = config[service_name]

    image_tag = f'{config["tag"]}-{chain_name}'
    build_path = str(docker_dir / config['docker_path'] / 'build')

    accumulated_status = ''
    for chunk in client.api.build(
        tag=image_tag, path=build_path, **kwargs):
        _str = chunk.decode('utf-8').rstrip()
        splt_str = _str.split('\n')

        for packet in splt_str:
            msg = json.loads(packet)
            status = msg.get('stream', '')

            if status:
                accumulated_status += status
                if '\n' in accumulated_status:
                    lines = accumulated_status.split('\n')
                    for line in lines[:-1]:
                        logger.info(line)
                    accumulated_status = lines[-1]

    try:
        client.images.get(image_tag)

    except docker.errors.NotFound:
        raise TEVMCBuildException(
            f'couldn\'t build container {image_tag} at '
            f'{build_path}')
