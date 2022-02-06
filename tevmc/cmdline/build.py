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

from tqdm import tqdm

from .cli import cli, get_docker_client
from .init import load_config_templates, load_docker_templates
from ..config import * 



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

    def tabulate(_str: str, amount=1) -> str:
        splt = _str.split('\n')
        nstr = splt[0] + '\n'
        for line in splt[1:]:
            tabs = '\t' * amount
            nstr += tabs + line + '\n'
        return nstr

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

    # rabbitmq
    rabbit_conf = config['rabbitmq']

    rabbit_dir = rabbit_conf['docker_path']
    rabbit_build_dir = rabbit_dir + '/' + 'build'
    rabbit_conf_dir  = rabbit_dir + '/' + rabbit_conf['conf_dir']

    subst = {
        'rabbitmq_port': rabbit_conf['host'].split(':')[-1],
        'rabbitmq_api_port': rabbit_conf['api'].split(':')[-1]
    }
    write_docker_template(f'{rabbit_build_dir}/Dockerfile', subst)
    write_docker_template(f'{rabbit_conf_dir}/rabbitmq.conf', subst)

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
    
    os.chown(host_dir, uid=1000, gid=1000)

    # kibana
    kibana_conf = config['kibana']

    kibana_dir = kibana_conf['docker_path']
    kibana_build_dir = kibana_dir + '/' + 'build'
    kibana_conf_dir  = kibana_dir + '/' + kibana_conf['conf_dir']

    subst = flatten('kibana', config) 
    write_docker_template(f'{kibana_build_dir}/Dockerfile', subst)
    write_docker_template(f'{kibana_conf_dir}/kibana.yml', subst)

    # nodeos
    chain_name = get_config('hyperion.chain.name', config)
    nodeos_conf = config['nodeos']
    ini_conf = nodeos_conf['ini']

    nodeos_dir = nodeos_conf['docker_path']
    nodeos_conf_dir = nodeos_dir + '/' + nodeos_conf['conf_dir']
    nodeos_build_dir = nodeos_dir + '/' + 'build'

    subst = {
        'nodeos_port': ini_conf['http_addr'].split(':')[-1],
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

    conf_str += '\n'

    for peer in subst['peers']:
        conf_str += f'p2p-peer-address = {peer}\n'

    with open(docker_dir / nodeos_conf_dir / 'config.ini', 'w+') as target_file:
        target_file.write(conf_str)

    # hyperion
    hyperion_conf = config['hyperion']

    hyperion_dir = hyperion_conf['docker_path']
    hyperion_build_dir = hyperion_dir + '/' + 'build'
    hyperion_conf_dir  = hyperion_dir + '/' + hyperion_conf['conf_dir']

    subst = {
        'api_port': config['hyperion']['chain']['router_port']
    }
    write_docker_template(f'{hyperion_build_dir}/Dockerfile', subst)

    # connections.json
    redis_conf = jsonize(flatten('redis', config))
    rabbitmq_conf = jsonize(flatten('rabbitmq', config))
    elasticsearch_conf = jsonize(flatten('elasticsearch', config))

    chains = {
        'hyperion_chains': tabulate(json.dumps({
        get_config('hyperion.chain.name', config): {
            'name':
                get_config('hyperion.chain.long_name', config),
            'chain_id':
                get_config('hyperion.chain.chain_hash', config),
            'http':
                get_config('hyperion.chain.http', config),
            'ship':
                get_config('hyperion.chain.ship', config),
            'WS_ROUTER_HOST':
                get_config('hyperion.chain.router_host', config),
            'WS_ROUTER_PORT':
                get_config('hyperion.chain.router_port', config),
        }}, indent=4))
    }

    subst = {}
    subst.update(redis_conf)
    subst.update(rabbitmq_conf)
    subst.update(elasticsearch_conf)
    subst.update(chains)

    write_config_file(
        'connections.json', hyperion_build_dir, subst)

    # ecosystem.config.js
    subst = {'name': get_config('hyperion.chain.name', config)}
    subst.update(timestamp)

    write_config_file(
        'ecosystem.config.js', hyperion_build_dir, subst)

    # telos-net.config.json
    hyperion_api_conf = jsonize(flatten(
        'hyperion',
        {'k': flatten('api', config['hyperion'])}, 'k'))

    # append chainname to actions, and deltas
    indexer_conf = flatten('indexer', config['hyperion'])

    blacklist_actions = []
    for act in indexer_conf['indexer_blacklists']['actions']:
        blacklist_actions.append(f'{chain_name}::{act}')

    indexer_conf['indexer_blacklists']['actions'] = blacklist_actions

    whitelist_actions = []
    for act in indexer_conf['indexer_whitelists']['actions']:
        whitelist_actions.append(f'{chain_name}::{act}')

    indexer_conf['indexer_whitelists']['actions'] = whitelist_actions

    blacklist_deltas = []
    for dlt in indexer_conf['indexer_blacklists']['deltas']:
        blacklist_deltas.append(f'{chain_name}::{dlt}')

    indexer_conf['indexer_blacklists']['deltas'] = blacklist_deltas

    whitelist_deltas = []
    for dlt in indexer_conf['indexer_whitelists']['deltas']:
        whitelist_deltas.append(f'{chain_name}::{dlt}')

    indexer_conf['indexer_whitelists']['deltas'] = whitelist_deltas

    hyperion_indexer_conf = jsonize(flatten(
        'hyperion',
        {'k': indexer_conf}, 'k'))

    telos_evm = get_config('hyperion.chain.telos-evm', config)
    telos_evm['chainId'] = get_config('hyperion.chain.chain_id', config)

    plugins = {
        'plugins': tabulate(json.dumps({
            'explorer': get_config('hyperion.chain.explorer', config),
            'telos-evm': telos_evm
    }, indent=4))}

    other = jsonize({
        'long_name': get_config('hyperion.chain.long_name', config),
        'name': get_config('hyperion.chain.name', config)
    })

    chains_path = docker_dir / hyperion_conf_dir
    chains_path.mkdir(parents=True, exist_ok=True)

    subst = {}
    subst.update(hyperion_api_conf)
    subst.update(hyperion_indexer_conf)
    subst.update(plugins)
    subst.update(other)
    with open(chains_path / f'{chain_name}.config.json', 'w+') as target_file:
        target_file.write(
            templates['telos-net.config.json'].substitute(**subst))

    # beats
    beats_conf = config['beats'] 
    beats_dir = docker_dir / beats_conf['docker_path']
    beats_conf_dir = beats_dir / beats_conf['conf_dir']
    os.chown(beats_conf_dir / 'filebeat.yml', uid=0, gid=0)


def perform_docker_build(target_dir, config, logger):
    perform_config_build(target_dir, config)

    docker_dir = target_dir / 'docker'
    docker_dir.mkdir(exist_ok=True)

    # docker build
    client = get_docker_client()

    builds = []
    for container, conf in config.items():
        if 'docker_path' in conf:
            builds.append({
                'tag': f'{conf["tag"]}-{config["hyperion"]["chain"]["name"]}',
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


class BuildInProgress:
    """ Helper class to manage build progress bar
    """

    def __init__(self):
        self.prev_progress = 0
        self.prev_total = 0
        self.current_progress = 0
        self.current_total = 0
        self.status = ''
        self.bar = tqdm(bar_format='{l_bar}{bar}')

    def set_status(self, status: str):
        new_status = format(
            f'{status[:MAX_STATUS_SIZE]}', f' <{MAX_STATUS_SIZE}')

        new_status = new_status.replace('\n', '')
        new_status = new_status.replace('\r', '')

        if new_status != self.status:
            self.status = new_status
            self.bar.set_description(desc=new_status)

    def update(self, update):
        if update.startswith('Step'):
            """Docker sends build updates with format
                'Step progress/total'
            Use it to update the progress bar.
            """
            step_info = update.split(' ')[1]
            step_info = step_info.split('/')
            progress = int(step_info[0])
            total = int(step_info[1])

            update = update.rstrip()
            
            if total != self.current_total:
                self.prev_total = self.current_total
                self.bar.reset(total=total)
                self.current_total = total

            if progress != self.current_progress:
                self.prev_progress = self.current_progress
                self.bar.update(n=progress)
                self.curent_progress = progress

            self.set_status(update) 

    def close(self):
        self.bar.close()


@cli.command()
@click.option(
    '--headless/--interactive', default=False,
    help='Display pretty output or just stream logs.')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
def build(headless, target_dir, config):
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

    rebuild_conf = prev_hash != curr_hash

    if rebuild_conf:
        config['metadata'] = {}
        config['metadata']['phash'] = curr_hash

        with open(target_dir / config_fname, 'w+') as uni_conf:
            uni_conf.write(json.dumps(config, indent=4))

        print('Rebuilding config files...', end='', flush=True)
        perform_config_build(target_dir, config)
        print('done.')

    docker_dir = target_dir / 'docker'
    docker_dir.mkdir(exist_ok=True)

    # docker build
    client = get_docker_client()

    builds = []
    for container, conf in config.items():
        if 'docker_path' in conf:
            builds.append({
                'tag': f'{conf["tag"]}-{config["hyperion"]["chain"]["name"]}',
                'path': str(docker_dir / conf['docker_path'] / 'build')
            })


    for build_args in builds:
        if not headless:
            stream = ''
            msg = f'building {build_args["tag"]}'
            bar = BuildInProgress()
            bar.set_status(msg)

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
                    if headless:
                        print(status, end='')
                    else:
                        stream += status
                        bar.update(status)
    
        if not headless:
            bar.set_status(f'built {build_args["tag"]}')
            bar.close()

        try:
            client.images.get(build_args['tag'])

        except docker.errors.NotFound:
            print(
                f'couldn\'t build container {build_args["tag"]} at '
                f'{build_args["path"]}')
            if not headless:
                print('build log:')
                print(stream)
            sys.exit(1)
