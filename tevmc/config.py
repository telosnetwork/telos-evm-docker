#!/usr/bin/env python3

DEFAULT_DOCKER_LABEL = {'created-by': 'tevmc'}
DEFAULT_FILTER = {'label': DEFAULT_DOCKER_LABEL}

DEFAULT_NETWORK_NAME = 'docker_hyperion'
EOSIO_VOLUME_NAME = 'eosio_volume'

HYPERION_API_LOG_VOLUME = 'hapi_log_volume'
HYPERION_INDEXER_LOG_VOLUME = 'hindexer_log_volume'

MAX_STATUS_SIZE = 54

DEFAULT_NODEOS_LOG_PATH = '/root/nodeos.log'


REDIS_TAG = 'redis:5.0.14-alpine'
RABBITMQ_TAG = 'rabbitmq:3.9.12-management'
ELASTICSEARCH_TAG = 'elasticsearch:7.16.3'
KIBANA_TAG = 'kibana:7.16.3'
EOSIO_TAG = 'eosio:2.1.0-evm'
BEATS_TAG = 'tevm:beats'
HYPERION_TAG = 'telos.net/hyperion:0.1.0'
TESTING_TAG = 'tevm:testing'
