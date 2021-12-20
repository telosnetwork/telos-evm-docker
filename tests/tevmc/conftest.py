#!/usr/bin/env python3

import pytest

from tevmc import TEVMController 


@pytest.fixture(scope='session')
def tevmc():
    with TEVMController() as _tevmc:
        yield _tevmc
