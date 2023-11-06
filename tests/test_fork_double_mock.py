#!/usr/bin/env python3

import pytest


def int_as_hash(n: int) -> str:
    return '{:064x}'.format(n)

max_block = 1100
blocks = (
    [int_as_hash(i)                      for i in range(max_block + 1)],
    [int_as_hash(i + int('1000000', 16)) for i in range(max_block + 1)],
    [int_as_hash(i + int('2000000', 16)) for i in range(max_block + 1)]
)

jumps = tuple([
    (20, 10),
    (21, 21)
])

@pytest.mark.start_block(1)
@pytest.mark.end_block(max_block)
@pytest.mark.blocks(blocks)
@pytest.mark.jumps(jumps)
def test_mock_ship_double_fork(ship_mocker):
    breakpoint()
