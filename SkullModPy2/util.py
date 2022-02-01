import math
import os
import struct
import sys

try:
    import winreg
except ImportError:
    # Non-Windows platform, handled in methods
    pass


# Registry
def get_reg_key_win(path, name):
    registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
    value, regtype = winreg.QueryValueEx(registry_key, name)
    winreg.CloseKey(registry_key)
    return value


# Steam
def get_steam_dir_win():
    try:
        # Get 64-bit steam dir
        return get_reg_key_win('SOFTWARE\\WOW6432Node\\Valve\\Steam', 'InstallPath')
    except OSError:
        try:
            # Get 32-bit steam dir
            return get_reg_key_win('SOFTWARE\\Valve\\Steam', 'InstallPath')
        except OSError:
            return None


# Naive parsing of libraryfolders.vdf
def parse_libraryfolders_vdf_win(steam_dir):
    libraryfolders_path = os.path.join(steam_dir, 'steamapps', 'libraryfolders.vdf')
    library_dirs = [steam_dir]

    with open(libraryfolders_path, 'r') as lf_file:
        for line in lf_file.readlines():
            if not line.lstrip().startswith('"path"'):
                continue
            # Get key and value
            segments = line.split('"')
            if len(segments) != 5:
                continue
            new_steam_dir = segments[3].replace('\\\\', '\\')
            if new_steam_dir not in library_dirs:
                library_dirs.append(new_steam_dir)
    return library_dirs


def get_data_directory():
    if sys.platform == 'darwin':  # MacOS
        # Return guessed default location for MacOS, path is blind guess based on PR from GitHub
        return '~/Library/Application Support/Steam/steamapps/common/Skullgirls/data01'
    steam_dir = get_steam_dir_win()
    if steam_dir is None:
        return None
    steam_libraries_list = parse_libraryfolders_vdf_win(steam_dir)
    # Try to find the steam library with the game
    for steam_library in steam_libraries_list:
        if os.path.exists(os.path.join(steam_library, 'steamapps', 'appmanifest_245170.acf')):
            return os.path.join(steam_library, 'steamapps', 'common', 'Skullgirls', 'data01')
    return None


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
