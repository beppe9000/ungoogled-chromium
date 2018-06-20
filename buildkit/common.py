# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common code and constants"""

import configparser
import enum
import os
import logging
import platform
from pathlib import Path

from .third_party import schema

# Constants

ENCODING = 'UTF-8' # For config files and patches

SEVENZIP_USE_REGISTRY = '_use_registry'

_ENV_FORMAT = "BUILDKIT_{}"

# Helpers for third_party.schema

def schema_dictcast(data):
    """Cast data to dictionary for third_party.schema and configparser data structures"""
    return schema.And(schema.Use(dict), data)

def schema_inisections(data):
    """Cast configparser data structure to dict and remove DEFAULT section"""
    return schema_dictcast({configparser.DEFAULTSECT: object, **data})

# Public classes

class BuildkitError(Exception):
    """Represents a generic custom error from buildkit"""

class BuildkitAbort(BuildkitError):
    """
    Exception thrown when all details have been logged and buildkit aborts.

    It should only be caught by the user of buildkit's library interface.
    """

class PlatformEnum(enum.Enum):
    """Enum for platforms that need distinction for certain functionality"""
    UNIX = 'unix' # Currently covers anything that isn't Windows
    WINDOWS = 'windows'

class ExtractorEnum: #pylint: disable=too-few-public-methods
    """Enum for extraction binaries"""
    SEVENZIP = '7z'
    TAR = 'tar'

# Public methods

def get_logger(name=__package__, initial_level=logging.DEBUG,
               prepend_timestamp=True, log_init=True):
    '''Gets the named logger'''

    logger = logging.getLogger(name)

    if logger.level == logging.NOTSET:
        logger.setLevel(initial_level)

        if not logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setLevel(initial_level)

            format_string = '%(levelname)s: %(message)s'
            if prepend_timestamp:
                format_string = '%(asctime)s - ' + format_string
            formatter = logging.Formatter(format_string)
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)
            if log_init:
                if name is None:
                    logger.debug("Initialized root logger")
                else:
                    logger.debug("Initialized logger '%s'", name)
    return logger

def dir_empty(path):
    """
    Returns True if the directory is empty; False otherwise

    path is a pathlib.Path or a string to a directory to test.
    """
    try:
        next(os.scandir(str(path)))
    except StopIteration:
        return True
    return False

def ensure_empty_dir(path, parents=False):
    """
    Makes a directory at path if it doesn't exist. If it exists, check if it is empty.

    path is a pathlib.Path to the directory.

    Raises FileExistsError if the directory already exists and is not empty
    When parents=False, raises FileNotFoundError if the parent directories do not exist
    """
    try:
        path.mkdir(parents=parents)
    except FileExistsError as exc:
        if not dir_empty(path):
            raise exc

def get_running_platform():
    """
    Returns a PlatformEnum value indicating the platform that buildkit is running on.

    NOTE: Platform detection should only be used when no cross-platform alternative is available.
    """
    uname = platform.uname()
    # detect native python and WSL
    if uname.system == 'Windows' or 'Microsoft' in uname.release:
        return PlatformEnum.WINDOWS
    # Only Windows and UNIX-based platforms need to be distinguished right now.
    return PlatformEnum.UNIX

def _read_version_ini():
    version_schema = schema.Schema(schema_inisections({
        'version': schema_dictcast({
            'chromium_version': schema.And(str, len),
            'release_revision': schema.And(str, len),
            schema.Optional('release_extra'): schema.And(str, len),
        })
    }))
    version_parser = configparser.ConfigParser()
    version_parser.read(
        str(Path(__file__).absolute().parent.parent / 'version.ini'),
        encoding=ENCODING)
    try:
        version_schema.validate(version_parser)
    except schema.SchemaError as exc:
        get_logger().error('version.ini failed schema validation')
        raise exc
    return version_parser

def get_chromium_version():
    """Returns the Chromium version."""
    return _VERSION_INI['version']['chromium_version']

def get_release_revision():
    """Returns the release revision."""
    return _VERSION_INI['version']['release_revision']

def get_release_extra(fallback=None):
    """
    Return the release revision extra info, or returns fallback if it is not defined.
    """
    return _VERSION_INI['version'].get('release_extra', fallback=fallback)

def get_version_string():
    """
    Returns a version string containing all information in a Debian-like format.
    """
    result = '{}-{}'.format(get_chromium_version(), get_release_revision())
    release_extra = get_release_extra()
    if release_extra:
        result += '~{}'.format(release_extra)
    return result

_VERSION_INI = _read_version_ini()
