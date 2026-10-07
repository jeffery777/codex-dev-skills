"""Bounded fixed control archives; never extract an archive into a host path."""
from __future__ import annotations

import io
import json
import math
import tarfile

MAX_JSON = 16384
MAX_ARCHIVE = 65536
FILE_NAMES = frozenset({'input.json', 'claim.json', 'completion.json'})


class ArchiveError(ValueError):
    pass


def _name(name):
    if type(name) is not str or name not in FILE_NAMES:
        raise ArchiveError('control-name-rejected')


def build_control_file(name, payload):
    """One deterministic USTAR root-owned 0600 regular file, no paths or links."""
    _name(name)
    if type(payload) is not bytes or not 0 < len(payload) <= MAX_JSON:
        raise ArchiveError('control-payload-bound')
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        member.mode = 0o600
        member.uid = member.gid = member.mtime = 0
        archive.addfile(member, io.BytesIO(payload))
    raw = output.getvalue()
    if len(raw) > MAX_ARCHIVE:
        raise ArchiveError('control-archive-bound')
    return raw


def _octal(field):
    value = field.strip(b'\x00 ')
    if not value or any(character not in b'01234567' for character in value):
        raise ArchiveError('control-tar-number-rejected')
    return int(value, 8)


def _text(field):
    value, separator, rest = field.partition(b'\x00')
    if separator and rest.strip(b'\x00'):
        raise ArchiveError('control-tar-name-rejected')
    return value


def _entry(raw):
    if type(raw) is not bytes or not 1536 <= len(raw) <= MAX_ARCHIVE or len(raw) % 512:
        raise ArchiveError('control-archive-bound')
    header = raw[:512]
    if header[257:265] != b'ustar\x0000':
        raise ArchiveError('control-tar-format-rejected')
    checksum = _octal(header[148:156])
    if checksum != sum(header[:148]) + 8 * ord(' ') + sum(header[156:]):
        raise ArchiveError('control-tar-checksum-rejected')
    if (_text(header[157:257]) or _text(header[345:500])
            or _octal(header[108:116]) != 0 or _octal(header[116:124]) != 0):
        raise ArchiveError('control-tar-metadata-rejected')
    size = _octal(header[124:136])
    if size > MAX_JSON:
        raise ArchiveError('control-payload-bound')
    end = 512 + size
    padded_end = 512 + ((size + 511) // 512) * 512
    # Reject truncated content, extra entries, PAX/GNU extensions, padding data
    # and absent end markers. Remaining blocks must all be zero.
    if len(raw) < padded_end + 1024 or any(raw[end:]):
        raise ArchiveError('control-tar-tail-rejected')
    return header, raw[512:end]


def read_control_file(raw, name):
    _name(name)
    header, payload = _entry(raw)
    if (_text(header[:100]) != name.encode('ascii')
            or header[156:157] not in (b'0', b'\x00')
            or _octal(header[100:108]) != 0o600 or not payload):
        raise ArchiveError('control-tar-file-rejected')
    return payload


def read_empty_control_directory(raw):
    """Docker cp of the fixed, root-owned, empty /control mount before start."""
    header, payload = _entry(raw)
    if (_text(header[:100]) not in (b'control', b'control/')
            or header[156:157] != b'5' or payload
            or _octal(header[100:108]) not in (0o700, 0o755)):
        raise ArchiveError('control-tar-directory-rejected')


def read_control_json(payload):
    if type(payload) is not bytes or not 0 < len(payload) <= MAX_JSON:
        raise ArchiveError('control-payload-bound')
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ArchiveError('control-json-duplicate-key')
            result[key] = value
        return result
    def constant(_):
        raise ArchiveError('control-json-number-rejected')
    def floating(raw):
        value = float(raw)
        if not math.isfinite(value):
            raise ArchiveError('control-json-number-rejected')
        return value
    try:
        value = json.loads(payload, object_pairs_hook=pairs, parse_constant=constant, parse_float=floating)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ArchiveError('control-json-rejected') from error
    if type(value) is not dict:
        raise ArchiveError('control-json-object-required')
    return value


def _limit(max_bytes):
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_JSON:
        raise ArchiveError('control-payload-bound')


def build_file(name, payload, max_bytes=MAX_JSON):
    _limit(max_bytes)
    if type(payload) is not bytes or len(payload) > max_bytes:
        raise ArchiveError('control-payload-bound')
    return build_control_file(name, payload)


def read_file(raw, name, max_bytes=MAX_JSON):
    _limit(max_bytes)
    payload = read_control_file(raw, name)
    if len(payload) > max_bytes:
        raise ArchiveError('control-payload-bound')
    return payload


def read_empty_directory(raw, name='control'):
    if name != 'control' or type(name) is not str:
        raise ArchiveError('control-name-rejected')
    return read_empty_control_directory(raw)


parse_json = read_control_json
