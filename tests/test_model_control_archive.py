import io
import pathlib
import sys
import tarfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
import model_control_archive as controls


def directory_archive(*, name='control/', mode=0o755, uid=0, extra=False):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as stream:
        item = tarfile.TarInfo(name); item.type = tarfile.DIRTYPE
        item.mode = mode; item.uid = uid
        stream.addfile(item)
        if extra:
            item = tarfile.TarInfo('input.json'); item.mode=0o600
            stream.addfile(item)
    return output.getvalue()


def header_edit(raw, start, end, value):
    changed = bytearray(raw)
    changed[start:end] = value.ljust(end-start, b'\x00')
    changed[148:156] = b'        '
    checksum = sum(changed[:512])
    changed[148:156] = f'{checksum:06o}\0 '.encode()
    return bytes(changed)


class ControlArchiveTests(unittest.TestCase):
    def setUp(self):
        self.payload = b'{"synthetic":true}'
        self.raw = controls.build_file('input.json', self.payload)

    def test_fixed_file_roundtrip_and_determinism(self):
        for name in controls.FILE_NAMES:
            raw = controls.build_file(name, self.payload)
            self.assertEqual(raw, controls.build_file(name, self.payload))
            self.assertEqual(controls.read_file(raw, name), self.payload)
            self.assertEqual(controls.parse_json(self.payload), {'synthetic': True})

    def test_names_payload_types_and_limits(self):
        for name in ['../input.json', '/input.json', 'other.json', None]:
            with self.subTest(name=name), self.assertRaises(controls.ArchiveError):
                controls.build_file(name, self.payload)
        for payload in [b'', 'json', bytearray(b'x'), b'x'*(controls.MAX_JSON+1)]:
            with self.subTest(payload_type=type(payload)), self.assertRaises(controls.ArchiveError):
                controls.build_file('input.json', payload)
        for limit in [True, 0, -1, controls.MAX_JSON+1]:
            with self.assertRaises(controls.ArchiveError):
                controls.read_file(self.raw, 'input.json', limit)
        with self.assertRaises(controls.ArchiveError):
            controls.read_file(self.raw, 'input.json', 1)

    def test_tar_bounds_truncation_and_missing_terminators(self):
        for raw in [None, bytearray(self.raw), self.raw[:512], self.raw[:1024],
                    self.raw[:-1], self.raw+b'\x00'*(controls.MAX_ARCHIVE+512)]:
            with self.subTest(kind=type(raw)), self.assertRaises(controls.ArchiveError):
                controls.read_file(raw, 'input.json')

    def test_bad_checksum_format_and_numbers(self):
        changed=bytearray(self.raw); changed[0]=ord('X')
        with self.assertRaises(controls.ArchiveError):
            controls.read_file(bytes(changed), 'input.json')
        for start,end,value in [(257,265,b'notustar'), (124,136,b'-1'),
                                (124,136,b'\x80'), (124,136,b'77777777777')]:
            with self.subTest(start=start,value=value), self.assertRaises(controls.ArchiveError):
                controls.read_file(header_edit(self.raw,start,end,value), 'input.json')

    def test_reject_nonregular_extensions_links_and_aliases(self):
        for start,end,value in [(156,157,b'1'),(156,157,b'2'),(156,157,b'5'),
                (156,157,b'x'),(156,157,b'g'),(156,157,b'L'),(156,157,b'K'),
                (157,257,b'other'),(345,500,b'prefix'),(0,100,b'../input.json'),
                (0,100,b'/input.json'),(0,100,b'completion.json')]:
            with self.subTest(value=value), self.assertRaises(controls.ArchiveError):
                controls.read_file(header_edit(self.raw,start,end,value), 'input.json')

    def test_reject_owner_mode_and_hidden_name_suffix(self):
        for start,end,value in [(108,116,b'0000001'),(116,124,b'0000001'),
                (100,108,b'0000644'),(100,108,b'0004600'),(0,100,b'input.json\x00evil')]:
            with self.subTest(value=value), self.assertRaises(controls.ArchiveError):
                controls.read_file(header_edit(self.raw,start,end,value), 'input.json')

    def test_padding_and_extra_entries_rejected(self):
        changed=bytearray(self.raw); changed[512+len(self.payload)]=1
        with self.assertRaises(controls.ArchiveError):
            controls.read_file(bytes(changed),'input.json')
        joined=self.raw[:1024]+controls.build_file('completion.json',self.payload)
        with self.assertRaises(controls.ArchiveError):
            controls.read_file(joined,'input.json')

    def test_empty_root_control_directory(self):
        for name in ['control','control/']:
            for mode in [0o700,0o755]:
                self.assertIsNone(controls.read_empty_directory(directory_archive(name=name,mode=mode)))
        for raw in [directory_archive(name='../control'),directory_archive(mode=0o777),
                    directory_archive(uid=1),directory_archive(extra=True),self.raw]:
            with self.assertRaises(controls.ArchiveError):
                controls.read_empty_directory(raw)
        with self.assertRaises(controls.ArchiveError):
            controls.read_empty_directory(directory_archive(),'/control')

    def test_json_rejects_duplicates_nonfinite_invalid_and_nonobjects(self):
        for raw in [b'{"x":1,"x":2}',b'{"nested":{"x":1,"x":2}}',
                    b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1e10000}',b'[]',b'null',
                    b'{',b'\xff',b'{} trailing',b'['*2000+b']'*2000,
                    b' '*controls.MAX_JSON+b'{}']:
            with self.subTest(raw=raw[:30]),self.assertRaises(controls.ArchiveError):
                controls.parse_json(raw)


if __name__ == '__main__':
    unittest.main()
