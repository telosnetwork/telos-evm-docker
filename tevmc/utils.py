
from decimal import localcontext

import re
import decimal
import numbers
import binascii
import collections.abc

from typing import (
    Any,
    AnyStr,
    NewType,
    Union,
)


HexStr = NewType('HexStr', str)
Primitives = Union[bytes, int, bool]

bytes_types = (bytes, bytearray)
integer_types = (int,)
text_types = (str,)
string_types = (bytes, str, bytearray)


def is_integer(value: Any) -> bool:
    return isinstance(value, integer_types) and not isinstance(value, bool)


def is_bytes(value: Any) -> bool:
    return isinstance(value, bytes_types)


def is_text(value: Any) -> bool:
    return isinstance(value, text_types)


def is_string(value: Any) -> bool:
    return isinstance(value, string_types)


def is_boolean(value: Any) -> bool:
    return isinstance(value, bool)


def is_dict(obj: Any) -> bool:
    return isinstance(obj, collections.abc.Mapping)


def is_list_like(obj: Any) -> bool:
    return not is_string(obj) and isinstance(obj, collections.abc.Sequence)


def is_list(obj: Any) -> bool:
    return isinstance(obj, list)


def is_tuple(obj: Any) -> bool:
    return isinstance(obj, tuple)


def is_null(obj: Any) -> bool:
    return obj is None


def is_number(obj: Any) -> bool:
    return isinstance(obj, numbers.Number)

# Units are in their own module here, so that they can keep this
# formatting, as this module is excluded from black in pyproject.toml
# fmt: off
units = {
    'wei':          decimal.Decimal('1'),  # noqa: E241
    'kwei':         decimal.Decimal('1000'),  # noqa: E241
    'babbage':      decimal.Decimal('1000'),  # noqa: E241
    'femtoether':   decimal.Decimal('1000'),  # noqa: E241
    'mwei':         decimal.Decimal('1000000'),  # noqa: E241
    'lovelace':     decimal.Decimal('1000000'),  # noqa: E241
    'picoether':    decimal.Decimal('1000000'),  # noqa: E241
    'gwei':         decimal.Decimal('1000000000'),  # noqa: E241
    'shannon':      decimal.Decimal('1000000000'),  # noqa: E241
    'nanoether':    decimal.Decimal('1000000000'),  # noqa: E241
    'nano':         decimal.Decimal('1000000000'),  # noqa: E241
    'szabo':        decimal.Decimal('1000000000000'),  # noqa: E241
    'microether':   decimal.Decimal('1000000000000'),  # noqa: E241
    'micro':        decimal.Decimal('1000000000000'),  # noqa: E241
    'finney':       decimal.Decimal('1000000000000000'),  # noqa: E241
    'milliether':   decimal.Decimal('1000000000000000'),  # noqa: E241
    'milli':        decimal.Decimal('1000000000000000'),  # noqa: E241
    'ether':        decimal.Decimal('1000000000000000000'),  # noqa: E241
    'kether':       decimal.Decimal('1000000000000000000000'),  # noqa: E241
    'grand':        decimal.Decimal('1000000000000000000000'),  # noqa: E241
    'mether':       decimal.Decimal('1000000000000000000000000'),  # noqa: E241
    'gether':       decimal.Decimal('1000000000000000000000000000'),  # noqa: E241
    'tether':       decimal.Decimal('1000000000000000000000000000000'),  # noqa: E241
}

class denoms:
    wei = int(units["wei"])
    kwei = int(units["kwei"])
    babbage = int(units["babbage"])
    femtoether = int(units["femtoether"])
    mwei = int(units["mwei"])
    lovelace = int(units["lovelace"])
    picoether = int(units["picoether"])
    gwei = int(units["gwei"])
    shannon = int(units["shannon"])
    nanoether = int(units["nanoether"])
    nano = int(units["nano"])
    szabo = int(units["szabo"])
    microether = int(units["microether"])
    micro = int(units["micro"])
    finney = int(units["finney"])
    milliether = int(units["milliether"])
    milli = int(units["milli"])
    ether = int(units["ether"])
    kether = int(units["kether"])
    grand = int(units["grand"])
    mether = int(units["mether"])
    gether = int(units["gether"])
    tether = int(units["tether"])


MIN_WEI = 0
MAX_WEI = 2 ** 256 - 1


def from_wei(number: int, unit: str) -> Union[int, decimal.Decimal]:
    """
    Takes a number of wei and converts it to any other ether unit.
    """
    if unit.lower() not in units:
        raise ValueError(
            "Unknown unit.  Must be one of {0}".format("/".join(units.keys()))
        )

    if number == 0:
        return 0

    if number < MIN_WEI or number > MAX_WEI:
        raise ValueError("value must be between 1 and 2**256 - 1")

    unit_value = units[unit.lower()]

    with localcontext() as ctx:
        ctx.prec = 999
        d_number = decimal.Decimal(value=number, context=ctx)
        result_value = d_number / unit_value

    return result_value


def to_wei(number: Union[int, float, str, decimal.Decimal], unit: str) -> int:
    """
    Takes a number of a unit and converts it to wei.
    """
    if unit.lower() not in units:
        raise ValueError(
            "Unknown unit.  Must be one of {0}".format("/".join(units.keys()))
        )

    if is_integer(number) or is_string(number):
        d_number = decimal.Decimal(value=number)
    elif isinstance(number, float):
        d_number = decimal.Decimal(value=str(number))
    elif isinstance(number, decimal.Decimal):
        d_number = number
    else:
        raise TypeError("Unsupported type.  Must be one of integer, float, or string")

    s_number = str(number)
    unit_value = units[unit.lower()]

    if d_number == decimal.Decimal(0):
        return 0

    if d_number < 1 and "." in s_number:
        with localcontext() as ctx:
            multiplier = len(s_number) - s_number.index(".") - 1
            ctx.prec = multiplier
            d_number = decimal.Decimal(value=number, context=ctx) * 10 ** multiplier
        unit_value /= 10 ** multiplier

    with localcontext() as ctx:
        ctx.prec = 999
        result_value = decimal.Decimal(value=d_number, context=ctx) * unit_value

    if result_value < MIN_WEI or result_value > MAX_WEI:
        raise ValueError("Resulting wei value must be between 1 and 2**256 - 1")

    return int(result_value)


def to_int(
    primitive: Primitives = None, hexstr: HexStr = None, text: str = None
) -> int:
    """
    Converts value to its integer representation.
    Values are converted this way:
     * primitive:
       * bytes, bytearrays: big-endian integer
       * bool: True => 1, False => 0
     * hexstr: interpret hex as integer
     * text: interpret as string of digits, like '12' => 12
    """
    if hexstr is not None:
        return int(hexstr, 16)
    elif text is not None:
        return int(text)
    elif isinstance(primitive, (bytes, bytearray)):
        return big_endian_to_int(primitive)
    elif isinstance(primitive, str):
        raise TypeError("Pass in strings with keyword hexstr or text")
    elif isinstance(primitive, (int, bool)):
        return int(primitive)
    else:
        raise TypeError(
            "Invalid type.  Expected one of int/bool/str/bytes/bytearray.  Got "
            "{0}".format(type(primitive))
        )


_HEX_REGEXP = re.compile("(0x)?[0-9a-f]*", re.IGNORECASE | re.ASCII)


def decode_hex(value: str) -> bytes:
    if not is_text(value):
        raise TypeError("Value must be an instance of str")
    non_prefixed = remove_0x_prefix(HexStr(value))
    # unhexlify will only accept bytes type someday
    ascii_hex = non_prefixed.encode("ascii")
    return binascii.unhexlify(ascii_hex)


def encode_hex(value: AnyStr) -> HexStr:
    if not is_string(value):
        raise TypeError("Value must be an instance of str or unicode")
    elif isinstance(value, (bytes, bytearray)):
        ascii_bytes = value
    else:
        ascii_bytes = value.encode("ascii")

    binary_hex = binascii.hexlify(ascii_bytes)
    return add_0x_prefix(HexStr(binary_hex.decode("ascii")))


def is_0x_prefixed(value: str) -> bool:
    if not is_text(value):
        raise TypeError(
            "is_0x_prefixed requires text typed arguments. Got: {0}".format(repr(value))
        )
    return value.startswith("0x") or value.startswith("0X")


def remove_0x_prefix(value: HexStr) -> HexStr:
    if is_0x_prefixed(value):
        return HexStr(value[2:])
    return value


def add_0x_prefix(value: HexStr) -> HexStr:
    if is_0x_prefixed(value):
        return value
    return HexStr("0x" + value)


def is_hexstr(value: Any) -> bool:
    if not is_text(value) or not value:
        return False
    return _HEX_REGEXP.fullmatch(value) is not None


def is_hex(value: Any) -> bool:
    if not is_text(value):
        raise TypeError(
            "is_hex requires text typed arguments. Got: {0}".format(repr(value))
        )
    if not value:
        return False
    return _HEX_REGEXP.fullmatch(value) is not None


# docker read logs with timeout
import queue
import logging
import threading
import time

from iterators import TimeoutIterator


def docker_stream_logs(client, container, timeout=30.0, from_latest=False):

    log_queue = queue.Queue()
    extra_args = {}
    if from_latest:
        extra_args['tail'] = 0

    def read_logs():
        try:
            stream = TimeoutIterator(
                container.logs(stream=True, follow=True, **extra_args),
                timeout=timeout,
                sentinel=None
            )
            for line in stream:
                if line == None:
                    break
                else:
                    log_queue.put(line)

        except docker.errors.APIError:
            ...

    log_thread = threading.Thread(target=read_logs)
    log_thread.start()

    while True:
        try:
            # Wait up to 30 seconds for a log line to become available
            yield log_queue.get(timeout=timeout)

        except queue.Empty:
            break

        # Check if the log thread has finished (i.e., if the log stream has closed)
        if not log_thread.is_alive() and log_queue.empty():
            break

    log_thread.join()
