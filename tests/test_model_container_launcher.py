"""Root launcher latch unit tests; no Docker or privilege mutation on host."""
import os
import pathlib
import stat
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'skills/loop-engineering/scripts'))
import model_container_launcher as launcher
import model_packet_store as packets


class Exit(BaseException):
    def __init__(self, code): self.code=code


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name)
        self.binding={'packet_id':'packet'}
        self.nonce='a'*64
        self.program=launcher.render(self.binding,'control-fixture',self.nonce,'noop')
        self.value={'schema_version':1,'binding':self.binding,'nonce':self.nonce,'volume':'control-fixture',
            'descriptor_sha256':'b'*64,'container_id':'c'*64,'launcher_sha256':launcher.contract_digest()}
        (self.root/'input.json').write_bytes(packets.canonical(self.value)); (self.root/'input.json').chmod(0o600)

    def run_launcher(self, *, fault='none', fork_fault=False, fsync_fault=False):
        realopen=os.open; realstat=os.stat; realfstat=os.fstat; realfsync=os.fsync
        calls=[]; exits=[]
        def rootstat(value):
            fields=['st_mode','st_ino','st_dev','st_nlink','st_size','st_atime_ns','st_mtime_ns','st_ctime_ns']
            return SimpleNamespace(**{key:getattr(value,key) for key in fields},st_uid=0,st_gid=0)
        def opening(path,*args,**kwargs):
            return realopen(str(self.root) if path=='/control' else path,*args,**kwargs)
        def fsync(fd):
            calls.append('fsync')
            if fsync_fault: raise OSError('synthetic-fsync-failure')
            return realfsync(fd)
        def fork():
            calls.append('fork')
            if fork_fault: raise OSError('synthetic-fork-failure')
            return 42
        def exiting(code):
            exits.append(code); raise Exit(code)
        with mock.patch.object(os,'open',side_effect=opening), mock.patch.object(os,'stat',side_effect=lambda *a,**k:rootstat(realstat(*a,**k))), mock.patch.object(os,'fstat',side_effect=lambda fd:rootstat(realfstat(fd))), mock.patch.object(os,'fsync',side_effect=fsync), mock.patch.object(os,'fork',side_effect=fork), mock.patch.object(os,'waitpid',return_value=(42,0)), mock.patch.object(os,'_exit',side_effect=exiting), mock.patch('signal.alarm'):
            namespace={}
            try: exec(launcher.render(self.binding,'control-fixture',self.nonce,'noop',fault),namespace)
            except Exit as result: return exits[0],calls
            finally:
                try: os.close(namespace['control'])
                except (KeyError,OSError): pass
            self.fail('launcher returned')

    def test_claim_is_durable_before_fork_and_duplicate_never_forks(self):
        code,calls=self.run_launcher(); self.assertEqual(code,0)
        self.assertGreaterEqual(calls.index('fork'),3)
        claim=(self.root/'claim.json').read_bytes(); completion=(self.root/'completion.json').read_bytes()
        self.assertEqual(stat.S_IMODE((self.root/'claim.json').stat().st_mode),0o600)
        code,calls=self.run_launcher(); self.assertEqual(code,73); self.assertNotIn('fork',calls)
        self.assertEqual((self.root/'claim.json').read_bytes(),claim)
        self.assertEqual((self.root/'completion.json').read_bytes(),completion)

    def test_partial_claim_fsync_fork_and_completion_crashes_never_replay(self):
        for fault in ['claim-created','claim-fsync','before-fork','completion-created']:
            with self.subTest(fault=fault):
                for name in ['claim.json','completion.json']:
                    path=self.root/name
                    if path.exists(): path.unlink()
                code,calls=self.run_launcher(fault=fault); self.assertEqual(code,74)
                self.assertTrue((self.root/'claim.json').exists())
                code,calls=self.run_launcher(); self.assertEqual(code,73); self.assertNotIn('fork',calls)

    def test_fork_failure_preserves_exclusive_claim(self):
        code,_=self.run_launcher(fork_fault=True); self.assertEqual(code,74)
        code,calls=self.run_launcher(); self.assertEqual(code,73); self.assertNotIn('fork',calls)

    def test_input_link_duplicate_keys_and_binding_drift_reject_before_claim(self):
        original=(self.root/'input.json').read_bytes()
        for value in [b'{"schema_version":1,"schema_version":1}',original.replace(b'"packet"',b'"other"')]:
            (self.root/'input.json').write_bytes(value)
            code,calls=self.run_launcher(); self.assertEqual(code,74); self.assertNotIn('fork',calls)
            self.assertFalse((self.root/'claim.json').exists())
        (self.root/'input.json').write_bytes(original)
        os.link(self.root/'input.json',self.root/'linked')
        code,calls=self.run_launcher(); self.assertEqual(code,74); self.assertNotIn('fork',calls)

    def test_fixed_source_compiles_and_rejects_unknown_recipe_or_fault(self):
        compile(self.program,'<fixed-launcher>','exec')
        for worker,fault in [('payload','none'),('noop','retry')]:
            with self.assertRaises(ValueError): launcher.render(self.binding,'control',self.nonce,worker,fault)
