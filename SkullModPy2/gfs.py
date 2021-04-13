from dataclasses import dataclass
import os
import struct

from SkullModPy2.util import read_int, read_pascal_string, write_pascal_string


FILE_IDENTIFIER = 'Reverge Package File'
FILE_EXTENSION = 'gfs'
FILE_VERSION = '1.1'


@dataclass
class GfsMetadataEntry:
    local_path: str
    offset: int
    size: int


@dataclass
class GfsFilesystemEntry:
    absolute_path: str
    size: int


def read_gfs_header(filename) -> list[GfsMetadataEntry]:
    with open(filename, 'rb') as file:
        data_offset = read_int(file, 4, False)
        if data_offset < 48:
            raise ValueError('GFS file header is too short')
        file_identifier_length = read_int(file, 8, False)
        if file_identifier_length != len(FILE_IDENTIFIER):
            raise ValueError('Not a GFS file')
        file_identifier = str(file.read(len(FILE_IDENTIFIER)), 'ascii')
        if file_identifier != FILE_IDENTIFIER:
            raise ValueError('Not a GFS file')
        file_version = read_pascal_string(file)
        if not file_version == FILE_VERSION:
            raise ValueError('Wrong GFS version')
        n_of_files = read_int(file, 8, False)

        # Process
        running_offset = data_offset
        references = []
        for _ in range(n_of_files):
            reference_path = read_pascal_string(file)
            reference_length = read_int(file, 8, False)
            reference_alignment = read_int(file, 4, False)
            # The alignment is already included
            running_offset += (reference_alignment - (running_offset % reference_alignment)) % reference_alignment
            references.append(GfsMetadataEntry(reference_path, running_offset, reference_length))

            running_offset += reference_length
    return references


def get_metadata(file_path: str) -> list[GfsMetadataEntry]:
    if file_path is None or not os.path.isfile(file_path) or not os.path.splitext(file_path)[1] == '.gfs':
        return None
    if os.path.getsize(file_path) < 48:
        return None
    try:
        return read_gfs_header(file_path)
    except Exception:
        return None


def get_files_in_dir(path: str) -> list[GfsFilesystemEntry]:
    # Generate file list for the directory
    result = []
    for root, subdirs, files in os.walk(path):
        # Go through all files in this directory
        # Save their relative positions and size
        for file in files:
            file_path = os.path.join(root, file)
            result.append(GfsFilesystemEntry(file_path, os.path.getsize(file_path)))
    return result


def write_content(base_path, entries: list[GfsFilesystemEntry], aligned: bool):
    base_path_len = len(base_path)
    alignment = 4096 if aligned else 1
    header_length = 51  # Base size (contains offset/file string/version/nOfFiles)
    for entry in entries:
        entry_path_len = len(entry.absolute_path[base_path_len+1:].replace('\\', '/'))
        header_length += 8 + entry_path_len + 8 + 4  # long strLength+fileName+long fileSize+uint alignment
    # Write header
    with open(base_path + '.gfs', 'wb') as f:
        f.write(struct.pack('>L', header_length))
        write_pascal_string(f, FILE_IDENTIFIER)
        write_pascal_string(f, FILE_VERSION)
        f.write(struct.pack('>Q', len(entries)))
        for entry in entries:
            write_pascal_string(f, entry.absolute_path[base_path_len+1:].replace('\\', '/'))
            f.write(struct.pack('>Q', entry.size))
            f.write(struct.pack('>L', alignment))
        if f.tell() % alignment != 0:  # Only align if alignment is needed
            f.write(b'\x00' * (alignment - (f.tell() % alignment)))  # Align header if needed
        for entry in entries:
            # Open file, read chunks, write chunks into this file
            with open(entry.absolute_path, 'rb') as data_file:
                bytes_read = data_file.read(4096)
                while bytes_read:
                    f.write(bytes_read)
                    bytes_read = data_file.read(4096)
            if f.tell() % alignment != 0:  # Only align if alignment is needed
                f.write(b'\x00' * (alignment - (f.tell() % alignment)))  # Write alignment


def export_files(file_path: str, entries: list[GfsMetadataEntry]) -> bool:
    base_path = os.path.splitext(file_path)[0]
    base_path_length = len(base_path)
    with open(file_path, 'rb') as source_file:
        for entry in entries:
            source_file.seek(entry.offset)
            absolute_path_entry = os.path.abspath(os.path.join(base_path, entry.local_path.replace('/', '\\')))

            if len(os.path.commonprefix([base_path, absolute_path_entry])) != base_path_length:
                # Directory traversal attack
                return False
            os.makedirs(os.path.dirname(absolute_path_entry), exist_ok=True)

            if entry.size < 0:
                return False
            with open(absolute_path_entry, 'wb', 4096) as output_file:
                for _ in range(int(entry.size / 4096)):
                    output_file.write(source_file.read(4096))
                output_file.write(source_file.read(entry.size % 4096))
    return True
