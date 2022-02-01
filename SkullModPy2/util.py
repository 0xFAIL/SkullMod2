import math
import os
import struct


def get_data_directory():
    return '~/Library/Application Support/Steam/steamapps/common/Skullgirls/data01'

def read_pascal_string(file) -> str:
    length = read_int(file, 8, False)
    if length < 0:
        raise ValueError('String length has to be 0 or more')
    return file.read(length).decode('ascii')


def write_pascal_string(file, string: str):
    ascii_string = string.encode('ascii')
    file.write(struct.pack('>Q', len(ascii_string)))
    file.write(ascii_string)


def read_int(file, length, signed) -> int:
    if length not in [4, 8]:
        raise ValueError('int length can only be 4 or 8')
    unpack_char = 'i' if length == 4 else 'q'
    if not signed:
        unpack_char = str.capitalize(unpack_char)

    return struct.unpack('>' + unpack_char, file.read(length))[0]


def human_readable_file_size(size_in_bytes: int) -> str:
    if size_in_bytes == 0:
        return '0B'
    size_name = ('B', 'KiB', 'MiB', 'GiB')
    entry_index = int(math.floor(math.log(size_in_bytes, 1024)))
    if entry_index == 0:
        number = size_in_bytes
    else:
        number = round(size_in_bytes / math.pow(1024, entry_index), 1)
    return '%s %s' % (number, size_name[entry_index])
