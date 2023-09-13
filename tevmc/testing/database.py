import time
import json
import math
import locale
import logging
from typing import List, Optional

from elasticsearch import Elasticsearch, NotFoundError

import traceback


locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

def format_block_numbers(block_num: int, evm_block_num: int) -> str:
    formatted_block_num = locale.format_string('%d', block_num, grouping=True)
    formatted_evm_block_num = locale.format_string('%d', evm_block_num, grouping=True)
    return f'[{formatted_block_num}|{formatted_evm_block_num}]'


def get_suffix(block_num, docs_per_index):
    return str(block_num // docs_per_index).zfill(8)


class StorageEosioDelta:
    def __init__(self, obj: dict):
        self.timestamp = obj.get('@timestamp')
        self.block_num = obj.get('block_num')
        self.global_block_num = obj.get('@global', {}).get('block_num')
        self.block_hash = obj.get('@blockHash')
        self.evm_block_hash = obj.get('@evmBlockHash')
        self.evm_prev_block_hash = obj.get('@evmPrevBlockHash')
        self.receipts_root_hash = obj.get('@receiptsRootHash')
        self.transactions_root = obj.get('@transactionsRoot')
        self.gas_used = obj.get('gasUsed')
        self.gas_limit = obj.get('gasLimit')
        self.size = obj.get('size')
        self.code = obj.get('code')
        self.table = obj.get('table')

    def block_nums_to_string(self):
        return format_block_numbers(self.block_num, self.global_block_num)


class InternalEvmTransaction:
    def __init__(self, obj: dict):
        self.call_type = obj.get('callType')
        self.from_address = obj.get('from')
        self.gas = obj.get('gas')
        self.input = obj.get('input')
        self.input_trimmed = obj.get('input_trimmed')
        self.to = obj.get('to')
        self.value = obj.get('value')
        self.gas_used = obj.get('gasUsed')
        self.output = obj.get('output')
        self.subtraces = obj.get('subtraces')
        self.trace_address = obj.get('traceAddress')
        self.type = obj.get('type')
        self.depth = obj.get('depth')
        self.extra = obj.get('extra')


class StorageEvmTransaction:
    def __init__(self, obj: dict):
        self.hash = obj.get('hash')
        self.from_address = obj.get('from')
        self.trx_index = obj.get('trx_index')
        self.block = obj.get('block')
        self.block_hash = obj.get('block_hash')
        self.to = obj.get('to')
        self.input_data = obj.get('input_data')
        self.input_trimmed = obj.get('input_trimmed')
        self.value = obj.get('value')
        self.nonce = obj.get('nonce')
        self.gas_price = obj.get('gas_price')
        self.gas_limit = obj.get('gas_limit')
        self.status = obj.get('status')
        self.itxs = [InternalEvmTransaction(tx) for tx in obj.get('itxs', [])]
        self.epoch = obj.get('epoch')
        self.createdaddr = obj.get('createdaddr')
        self.gasused = obj.get('gasused')
        self.gasusedblock = obj.get('gasusedblock')
        self.charged_gas_price = obj.get('charged_gas_price')
        self.output = obj.get('output')
        self.logs = obj.get('logs')
        self.logs_bloom = obj.get('logsBloom')
        self.errors = obj.get('errors')
        self.value_d = obj.get('value_d')
        self.raw = obj.get('raw')
        self.v = obj.get('v')
        self.r = obj.get('r')
        self.s = obj.get('s')

class StorageEosioAction:
    def __init__(self, obj: dict):
        self.timestamp = obj.get('@timestamp')
        self.trx_id = obj.get('trx_id')
        self.action_ordinal = obj.get('action_ordinal')
        self.signatures = obj.get('signatures')
        self.raw = StorageEvmTransaction(obj.get('@raw'))


def index_to_suffix_num(index: str) -> int:
    splt_index = index.split('-')
    suffix = splt_index[-1]
    return int(suffix)


class ElasticDataEmptyError(BaseException):
    ...


class ElasticDataIntegrityError(BaseException):
    ...


class ESDuplicatesFound(ElasticDataIntegrityError):

    def __init__(
        self,
        message: str,
        delta_dups: List[int],
        action_dups: List[int]
    ):
        super().__init__(message)
        self.delta_dups = delta_dups
        self.action_dups = action_dups

class ESGapFound(ElasticDataIntegrityError):

    def __init__(
        self,
        message: str,
        start: int
    ):
        super().__init__(message)
        self.start = start



class ElasticDriver:

    def __init__(self, config: dict):
        self.config = config
        self.chain_name = config['telos-evm-rpc']['elastic_prefix']
        self.docs_per_index = 10_000_000

        es_config = config['elasticsearch']
        self.elastic = Elasticsearch(
            f'{es_config["protocol"]}://{es_config["host"]}',
            basic_auth=(
                es_config['user'], es_config['pass']
            )
        )

    def tx_from_hash(self, h: str):
        try:
            result = self.elastic.search(
                index=f'{self.chain_name}-action-*',
                size=1,
                query={
                    'match': {
                        '@raw.hash': h
                    }
                }
            )

            logging.info(f'tx_from_hash: {h}')
            logging.info(result)

            if 'hits' not in result:
                return None

            if 'hits' not in result['hits']:
                return None

            if len(result['hits']['hits']) == 0:
                return None

            return StorageEosioAction(result['hits']['hits'][0]['_source'])

        except BaseException as error:
            logging.error(traceback.format_exc())
            logging.error(error)
            return None

    def block_from_evm_num(self, num: int):
        try:
            result = self.elastic.search(
                index=f'{self.chain_name}-delta-*',
                size=1,
                query={
                    'match': {
                        '@global.block_num': num
                    }
                }
            )

            logging.info(f'block_from_evm_num: {num}')
            logging.info(result)

            if 'hits' not in result:
                return None

            if 'hits' not in result['hits']:
                return None

            if len(result['hits']['hits']) == 0:
                return None

            return StorageEosioDelta(result['hits']['hits'][0]['_source'])

        except BaseException as error:
            logging.error(traceback.format_exc())
            logging.error(error)
            return None

    def get_ordered_delta_indices(self):
        index_pattern = f'{self.chain_name}-delta-*'
        delta_indices = self.elastic.indices.get(index=index_pattern)
        delta_indices = list(delta_indices.keys())
        delta_indices.sort(key=lambda x: index_to_suffix_num(x))

        return delta_indices

    def get_first_indexed_block(self):
        indices = self.get_ordered_delta_indices()

        if len(indices) == 0:
            return None

        first_index = indices.pop(0)
        try:
            result = self.elastic.search(
                index=first_index,
                size=1,
                sort=[
                    {'block_num': {'order': 'asc'}}
                ]
            )

            if result.get('hits', {}).get('hits') and len(result.get('hits', {}).get('hits')) == 0:
                return None

            return StorageEosioDelta(result.get('hits', {}).get('hits', [])[0].get('_source'))

        except BaseException as error:
            logging.error(traceback.format_exc())
            logging.error(error)
            return None

    def get_last_indexed_block(self):
        indices = self.get_ordered_delta_indices()
        if len(indices) == 0:
            return None

        for i in range(len(indices) - 1, -1, -1):
            last_index = indices[i]
            try:
                result = self.elastic.search(
                    index=last_index,
                    size=1,
                    sort=[
                        {'block_num': {'order': 'desc'}}
                    ]
                )

                hits = result.get('hits', {}).get('hits', [])
                if not hits or len(hits) == 0:
                    continue

                block_doc = hits[0].get('_source')
                logging.debug(f'getLastIndexedBlock:\n{json.dumps(block_doc, indent=4)}')

                return StorageEosioDelta(block_doc)

            except BaseException as error:
                logging.error(traceback.format_exc())
                logging.error(error)
                return None

        return None

    def find_gap_in_indices(self):
        delta_indices = self.get_ordered_delta_indices()
        logging.debug('delta indices: ')
        logging.debug(json.dumps(delta_indices, indent=4))
        for i in range(1, len(delta_indices)):
            previous_index_suffix_num = index_to_suffix_num(delta_indices[i - 1])
            current_index_suffix_num = index_to_suffix_num(delta_indices[i])

            if current_index_suffix_num - previous_index_suffix_num > 1:
                return {
                    'gapStart': previous_index_suffix_num,
                    'gapEnd': current_index_suffix_num
                }

        # Return None if no gaps found
        return None

    def run_histogram_gap_check(self, lower: int, upper: int, interval: int):
        index_name = f'{self.chain_name}-delta-*'
        body = {
            'query': {
                'range': {
                    '@global.block_num': {
                        'gte': lower,
                        'lte': upper
                    }
                }
            },
            'aggs': {
                'block_histogram': {
                    'histogram': {
                        'field': '@global.block_num',
                        'interval': interval,
                        'min_doc_count': 0
                    },
                    'aggs': {
                        'min_block': {
                            'min': {
                                'field': '@global.block_num'
                            }
                        },
                        'max_block': {
                            'max': {
                                'field': '@global.block_num'
                            }
                        }
                    }
                }
            }
        }
        results = self.elastic.search(index=index_name, size=0, **body)

        buckets = results['aggregations']['block_histogram']['buckets']

        logging.debug(f'runHistogramGapCheck: {lower}-{upper}, interval: {interval}')
        logging.debug(json.dumps(buckets, indent=4))

        return buckets

    def find_duplicate_deltas(self, lower: int, upper: int):
        index_name = f'{self.chain_name}-delta-*'
        body = {
            'query': {
                'range': {
                    '@global.block_num': {
                        'gte': lower,
                        'lte': upper
                    }
                }
            },
            'aggs': {
                'duplicate_blocks': {
                    'terms': {
                        'field': '@global.block_num',
                        'min_doc_count': 2,
                        'size': 100
                    }
                }
            }
        }
        results = self.elastic.search(index=index_name, size=0, **body)

        if 'aggregations' in results:
            buckets = results['aggregations']['duplicate_blocks']['buckets']
            logging.debug(f'findDuplicateDeltas: {lower}-{upper}')
            return [bucket['key'] for bucket in buckets]
        else:
            return []

    def find_duplicate_actions(self, lower: int, upper: int):
        index_name = f'{self.chain_name}-action-*'
        body = {
            'query': {
                'range': {
                    '@raw.block': {
                        'gte': lower,
                        'lte': upper
                    }
                }
            },
            'aggs': {
                'duplicate_txs': {
                    'terms': {
                        'field': '@raw.hash',
                        'min_doc_count': 2,
                        'size': 100
                    }
                }
            }
        }
        results = self.elastic.search(index=index_name, size=0, **body)

        if 'aggregations' in results:
            buckets = results['aggregations']['duplicate_txs']['buckets']
            logging.debug(f'findDuplicateActions: {lower}-{upper}')
            return [bucket['key'] for bucket in buckets]
        else:
            return []

    def check_gaps(self, lower_bound: int, upper_bound: int, interval: int) -> Optional[int]:

        interval = math.ceil(interval)

        # Base case
        if interval == 1:
            return lower_bound

        middle = (upper_bound + lower_bound) // 2

        logging.debug(f'calculated middle {middle}')

        logging.debug('first half')
        # Recurse on the first half
        lower_buckets = self.run_histogram_gap_check(lower_bound, middle, interval // 2)
        if len(lower_buckets) == 0:
            return middle  # Gap detected
        elif lower_buckets[-1]['max_block']['value'] < middle:
            lower_gap = self.check_gaps(lower_bound, middle, interval // 2)
            if lower_gap:
                return lower_gap

        logging.debug('second half')
        # Recurse on the second half
        upper_buckets = self.run_histogram_gap_check(middle + 1, upper_bound, interval // 2)
        if len(upper_buckets) == 0:
            return middle + 1  # Gap detected
        elif upper_buckets[0]['min_block']['value'] > middle + 1:
            upper_gap = self.check_gaps(middle + 1, upper_bound, interval // 2)
            if upper_gap:
                return upper_gap

        # Check for gap between the halves
        if (lower_buckets[-1]['max_block']['value'] + 1) < upper_buckets[0]['min_block']['value']:
            return lower_buckets[-1]['max_block']['value']

        # Find gaps inside bucket by doc_count
        buckets = lower_buckets + upper_buckets
        for i in range(len(buckets)):
            if buckets[i]['doc_count'] != (buckets[i]['max_block']['value'] - buckets[i]['min_block']['value']) + 1:
                inside_gap = self.check_gaps(buckets[i]['min_block']['value'], buckets[i]['max_block']['value'], interval // 2)
                if inside_gap:
                    return inside_gap

        # No gap found
        return None

    def full_integrity_check(self):
        lower_bound_doc = self.get_first_indexed_block()
        upper_bound_doc = self.get_last_indexed_block()

        if not lower_bound_doc or not upper_bound_doc:
            return None

        lower_bound = lower_bound_doc.global_block_num
        upper_bound = upper_bound_doc.global_block_num
        step = 10_000_000

        delta_duplicates = []
        action_duplicates = []

        for current_lower in range(lower_bound, upper_bound, step):
            current_upper = min(current_lower + step, upper_bound)

            delta_duplicates += self.find_duplicate_deltas(current_lower, current_upper)
            action_duplicates += self.find_duplicate_actions(current_lower, current_upper)

        if len(delta_duplicates) > 0:
            logging.error(f'block duplicates found: {json.dumps(delta_duplicates)}')

        if len(action_duplicates) > 0:
            logging.error(f'tx duplicates found: {json.dumps(action_duplicates)}')

        if len(delta_duplicates) + len(action_duplicates) > 0:
            raise ESDuplicatesFound(
                f'Duplicates found! {action_duplicates}, {delta_duplicates}',
                delta_duplicates, action_duplicates
            )

        if upper_bound - lower_bound < 2:
            return

        # First just check if whole indices are missing
        gap = self.find_gap_in_indices()
        if gap:
            logging.debug('whole index seems to be missing')
            lower = gap['gapStart'] * self.docs_per_index
            upper = (gap['gapStart'] + 1) * self.docs_per_index
            agg = self.run_histogram_gap_check(
                lower, upper, self.docs_per_index)
            gap = agg[0]['max_block']['value'] + 1
            raise ESGapFound(f'Gap found! {int(gap)}', int(gap))

        initial_interval = upper_bound - lower_bound

        logging.info(f'starting full gap check from {lower_bound} to {upper_bound}')

        gap = self.check_gaps(lower_bound, upper_bound, initial_interval)
        if gap:
            raise ESGapFound(f'Gap found! {int(gap)}', int(gap))

    def _purge_blocks_newer_than(self, block_num, evm_block_num):
        target_suffix = get_suffix(block_num, self.docs_per_index)
        delta_index = f'{self.chain_name}-delta-v1.5-{target_suffix}'
        action_index = f'{self.chain_name}-action-v1.5-{target_suffix}'

        try:
            self._delete_by_query(delta_index, 'block_num', block_num)

        except NotFoundError:
            ...

        try:
            self._delete_by_query(action_index, '@raw.block', evm_block_num)

        except NotFoundError:
            ...

    def _delete_by_query(self, index, field, value):
        try:
            result = self.elastic.delete_by_query(
                index=index,
                query={
                    'range': {
                        field: {
                            'gte': value
                        }
                    }
                },
                conflicts='proceed',
                refresh=True,
                error_trace=True
            )
            logging.debug(f'delete result: {result}')
        except Exception as e:
            if e.__class__.__name__ != 'ResponseError' or e.info['error']['type'] != 'index_not_found_exception':
                raise e

    def _purge_indices_newer_than(self, block_num):
        logging.info(f'purging indices in db from block {block_num}...')
        target_suffix = get_suffix(block_num, self.docs_per_index)
        target_num = int(target_suffix)
        delete_list = []

        delete_list += self._collect_indices_to_delete('delta-v1.5', target_num)
        delete_list += self._collect_indices_to_delete('action-v1.5', target_num)

        if delete_list:
            delete_result = self.elastic.indices.delete(index=delete_list)
            logging.info(f'deleted indices result: {delete_result}')

        return delete_list

    def _collect_indices_to_delete(self, subfix, target_num):
        indices = self.elastic.cat.indices(
            index=f'{self.chain_name}-{subfix}-*',
            format='json'
        )
        return [index['index'] for index in indices if index_to_suffix_num(index['index']) > target_num]

    def purge_newer_than(self, block_num, evm_block_num):
        self._purge_indices_newer_than(block_num)
        self._purge_blocks_newer_than(block_num, evm_block_num)

    def repair_data(self):
        try:
            self.full_integrity_check()
            doc = self.get_last_indexed_block()
            if doc:
                return doc.block_num, doc.global_block_num

            else:
                raise ElasticDataEmptyError()

        except ESGapFound as err:
            logging.info(err)

            bnum = err.start
            doc = self.block_from_evm_num(bnum)
            backstep = 10
            exp = 1
            while not doc and exp < 6:
                logging.info(f'block #{bnum} query returned None, trying older block...')
                bnum -= backstep ** exp
                exp += 1
                time.sleep(1)
                doc = self.block_from_evm_num(bnum)

            if not doc:
                raise ElasticDataIntegrityError('Gap found but couldn\'t find last valid block!')

        except ESDuplicatesFound as err:
            logging.info(err)
            # If duplicate is found could be by tx hash or block num
            # in both cases we gotta get the delta document for the 
            # block in question
            min_block = None

            act_block = None
            if len(err.action_dups) > 0:
                act_evm_block = es.tx_from_hash(err.action_dups[0]).raw.block
                act_block = es.block_from_evm_num(act_evm_block)
                min_block = act_block

            delta_block = None
            if len(err.delta_dups) > 0:
                delta_block = es.block_from_evm_num(err.delta_dups[0])

                if min_block and min_block.block_num > delta_block.block_num:
                    min_block = delta_block

            assert min_block  # Min block must be non null

            doc = min_block

        self.purge_newer_than(doc.block_num, doc.global_block_num)

        # return last valid block nums
        return doc.block_num - 1, doc.global_block_num - 1
