import json
import math
import locale
import logging
from typing import Optional

from elasticsearch import Elasticsearch


locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

def format_block_numbers(block_num: int, evm_block_num: int) -> str:
    formatted_block_num = locale.format_string('%d', block_num, grouping=True)
    formatted_evm_block_num = locale.format_string('%d', evm_block_num, grouping=True)
    return f'[{formatted_block_num}|{formatted_evm_block_num}]'


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


def index_to_suffix_num(index: str) -> int:
    splt_index = index.split('-')
    suffix = splt_index[-1]
    return int(suffix)


class ElasticDataIntegrityError(BaseException):
    ...


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

        except Exception as error:
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

            except Exception as error:
                logging.error(error)
                raise error

        return None

    def find_gap_in_indices(self):
        delta_indices = self.get_ordered_delta_indices()
        logging.debug('delta indices: ')
        logging.debug(json.dumps(delta_indices, indent=4))
        for i in range(1, len(delta_indices)):
            previous_index_suffix_num = index_to_suffix_num(delta_indices[i - 1]['index'])
            current_index_suffix_num = index_to_suffix_num(delta_indices[i]['index'])

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
            raise ElasticDataIntegrityError(
                f'Duplicates found! {action_duplicates}, {delta_duplicates}')

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
            return agg[0]['max_block']['value']

        initial_interval = upper_bound - lower_bound

        logging.info(f'starting full gap check from {lower_bound} to {upper_bound}')

        gap = self.check_gaps(lower_bound, upper_bound, initial_interval)
        if gap:
            raise ElasticDataIntegrityError(f'Gap found! {int(gap)}')

