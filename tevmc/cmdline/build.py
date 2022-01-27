#!/usr/bin/env python3

import sys
import json

import click
import docker

from typing import Dict, Any
from pathlib import Path
from datetime import datetime

from tqdm import tqdm

from .cli import cli, get_docker_client
from .init import load_config_templates, load_docker_templates
from ..config import * 


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
    try:
        config = load_config(target_dir, config)

    except FileNotFoundError:
        print('Config not found.')
        sys.exit(1)
    
    target_dir = Path(target_dir).resolve()

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

    def write_docker_template(file: str, subst: Dict[str, Any]):
        with open(docker_dir / file, 'w+') as conf_file:
            conf_file.write(
                docker_templates[file].substitute(**subst))


    # redis
    subst = {
        'redis_port': config['redis']['port'],
        'redis_host': config['redis']['host']
    }   
    write_docker_template('redis/Dockerfile', subst)
    write_docker_template('redis/redis.conf', subst)

    # rabbitmq
    subst = {
        'rabbitmq_port': config['rabbitmq']['host'].split(':')[-1],
        'rabbitmq_api_port': config['rabbitmq']['api'].split(':')[-1]
    }
    write_docker_template('rabbitmq/Dockerfile', subst)
    write_docker_template('rabbitmq/rabbitmq.conf', subst)

    # elasticsearch 
    subst = {
        'elasticsearch_port': config['elasticsearch']['host'].split(':')[-1]
    }
    write_docker_template('elasticsearch/Dockerfile', subst)
    write_docker_template('elasticsearch/elasticsearch.yml', subst)

    # kibana
    subst = {
        'kibana_host': config['kibana']['host'],
        'kibana_port': config['kibana']['port']
    }
    write_docker_template('kibana/Dockerfile', subst)
    write_docker_template('kibana/kibana.yml', subst)

    # nodeos
    chain_name = get_config('hyperion.chain.name', config)

    subst = {
        'nodeos_port': config['nodeos']['ini']['http_addr'].split(':')[-1],
        'nodeos_history_port': config['nodeos']['ini']['history_endpoint'].split(':')[-1]
    }
    write_docker_template('eosio/Dockerfile', subst)

    # hyperion
    subst = {
        'api_port': config['hyperion']['chain']['router_port']
    }
    write_docker_template('hyperion/Dockerfile', subst)

    # logrotate.conf
    write_config_file(
        'logrotate.conf',
        'eosio',
        {'nodeos_log_path': get_config('nodeos.log_path', config)})

    # nodeos.config.ini
    subst = get_config('nodeos.ini', config) | timestamp

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

    with open(docker_dir / 'eosio/config.ini', 'w+') as target_file:
        target_file.write(conf_str)

    # hyperion

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

    write_config_file(
        'connections.json',
        'hyperion/config',
        redis_conf | rabbitmq_conf | elasticsearch_conf | chains)

    # ecosystem.config.js
    write_config_file(
        'ecosystem.config.js',
        'hyperion/config',
        {'name': get_config('hyperion.chain.name', config)} |
        timestamp)

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

    with open(docker_dir / f'hyperion/config/chains/{chain_name}.config.json', 'w+') as target_file:
        target_file.write(templates['telos-net.config.json'].substitute(
            **(hyperion_api_conf | hyperion_indexer_conf | plugins | other)))

    # docker build
    client = get_docker_client()

    builds = []
    for container, conf in config.items():
        if 'docker_path' in conf:
            builds.append({
                'tag': f'{conf["tag"]}-{config["hyperion"]["chain"]["name"]}',
                'path': str(docker_dir / conf['docker_path'])
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
