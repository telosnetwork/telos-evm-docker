
from decimal import localcontext
from pathlib import Path

import re
import decimal
import numbers
import binascii
import collections.abc

from typing import (
    Any,
    List,
    AnyStr,
    NewType,
    Union,
    Tuple,
    Iterator
)

from docker.errors import DockerException


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
    'telos':        decimal.Decimal('100000000000000'),  # noqa: E241
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
    telos = int(units["telos"])
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


import struct
import logging

import requests_unixsocket

from requests.exceptions import Timeout

from docker.models.containers import Container


def _parse_docker_log(data):
    '''Parses Docker logs by handling Docker's log protocol.

    Docker prefixes each log entry with an 8-byte header:
    - 1 byte: Stream type (STDIN, STDOUT, STDERR)
    - 7 bytes: Size of the message that follows

    Args:
        data (bytes): The raw logs data with Docker's headers.

    Yields:
        str: The parsed log messages.
    '''
    while data:
        # Extract header from data
        header = data[:8]
        _, length = struct.unpack('>BxxxL', header)

        # Extract the actual log message based on the length from the header
        message = data[8:8+length].decode('utf-8', errors='replace')

        # Advance the buffer to next log entry
        data = data[8+length:]

        yield message


def docker_stream_logs(container, timeout=30.0, lines=0, from_latest=False):
    '''Streams logs from a running Docker container.

    Args:
        container (container): Docker container object.
        timeout (float, optional): Time to wait between log messages. Default to 30.0 seconds.
        from_latest (bool, optional): Only fetch logs since the last log. Default to False.

    Yields:
        str: The log messages.

    Raises:
        DockerException: If the container is not running.
        StopIteration: If no logs are received within the timeout period.
    '''
    container.reload()

    if container.status != 'running':
        raise DockerException(
            f'Tried to stream logs but container {container.name} is stopped')

    # Set up a session to use the Docker Unix socket
    session = requests_unixsocket.Session()

    url = f'http+unix://%2Fvar%2Frun%2Fdocker.sock/containers/{container.name}/logs'

    # Parameters for the log request
    params = {
        'stdout': '1',
        'stderr': '1',
        'follow': '1'
    }

    # If only logs from the latest are required
    if from_latest:
        params['tail'] = str(lines)

    response = session.get(
        url, params=params, stream=True, timeout=timeout)

    try:
        data_buffer = b''
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                data_buffer += chunk
                for message in _parse_docker_log(data_buffer):
                    yield message
                    # Adjust the buffer after reading the message
                    data_buffer = data_buffer[len(message)+8:]

    except Timeout:
        raise StopIteration(f'No logs received for {timeout} seconds.')


def docker_open_process(
    client,
    cntr,
    cmd: List[str],
    **kwargs
) -> Tuple[str, Iterator[str]]:
    """Begin running the command inside the container, return the
    internal docker process id, and a stream for the standard output.
    :param cmd: List of individual string forming the command to execute in
        the testnet container shell.
    :param kwargs: A variable number of key word arguments can be
        provided, as this function uses `exec_create & exec_start docker APIs
        <https://docker-py.readthedocs.io/en/stable/api.html#module-dock
        er.api.exec_api>`_.
    :return: A tuple with the process execution id and the output stream to
        be consumed.
    :rtype: :ref:`typing_exe_stream`
    """
    exec_id = client.api.exec_create(cntr.id, cmd, **kwargs)
    exec_stream = client.api.exec_start(exec_id=exec_id, stream=True)
    return exec_id['Id'], exec_stream

def docker_wait_process(
    client,
    exec_id: str,
    exec_stream: Iterator[str],
    logger=None
) -> Tuple[int, str]:
    """Collect output from process stream, then inspect process and return
    exitcode.
    :param exec_id: Process execution id provided by docker engine.
    :param exec_stream: Process output stream to be consumed.
    :return: Exitcode and process output.
    :rtype: :ref:`typing_exe_result`
    """
    if logger is None:
        logger = logging.getLogger()

    out = ''
    for chunk in exec_stream:
        msg = chunk.decode('utf-8')
        out += msg

    info = client.api.exec_inspect(exec_id)

    ec = info['ExitCode']
    if ec != 0:
        logger.warning(out.rstrip())

    return ec, out

import tarfile


def docker_move_into(
    client,
    container: Union[str, Container],
    src: Union[str, Path],
    dst: Union[str, Path]
):
    tmp_name = random_string(size=32)
    archive_loc = Path(f'/tmp/{tmp_name}.tar.gz').resolve()

    with tarfile.open(archive_loc, mode='w:gz') as archive:
        archive.add(src, recursive=True)

    with open(archive_loc, 'rb') as archive:
        binary_data = archive.read()

    archive_loc.unlink()

    if isinstance(container, Container):
        container = container.id

    client.api.put_archive(container, dst, binary_data)


def docker_move_out(
    container: Union[str, Container],
    src: Union[str, Path],
    dst: Union[str, Path]
):
    tmp_name = random_string(size=32)
    archive_loc = Path(f'/tmp/{tmp_name}.tar.gz').resolve()

    bits, _ = container.get_archive(src, encode_stream=True)

    with open(archive_loc, mode='wb+') as archive:
        for chunk in bits:
            archive.write(chunk)

    extract_path = Path(dst).resolve()

    if extract_path.is_file():
        extract_path = extract_path.parent

    with tarfile.open(archive_loc, 'r') as archive:
        archive.extractall(path=extract_path)

    archive_loc.unlink()


# recursive compare two dicts
def deep_dict_equal(dict1, dict2):
    if set(dict1.keys()) != set(dict2.keys()):
        return False
    for key, value1 in dict1.items():
        value2 = dict2[key]
        if isinstance(value1, dict) and isinstance(value2, dict):
            if not deep_dict_equal(value1, value2):
                return False
        elif isinstance(value1, list) and isinstance(value2, list):
            if len(value1) != len(value2):
                return False
            for item1, item2 in zip(value1, value2):
                if isinstance(item1, dict) and isinstance(item2, dict):
                    if not deep_dict_equal(item1, item2):
                        return False
                elif item1 != item2:
                    return False
        elif value1 != value2:
            return False
    return True
