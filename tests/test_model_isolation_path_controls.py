"""Counterexamples for fixed synthetic exact-path controls; no Docker calls."""
import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

MODULE=pathlib.Path(__file__).resolve().parents[1]/'scripts/verify-model-isolation-path-controls.py'
SPEC=importlib.util.spec_from_file_location('path_controls',MODULE)
control=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)


def result(targets,positive):
    cases=[]
    for label,path in zip(control.LABELS,targets,strict=True):
        cases.append(dict(label=label,target=str(path),read=label+'\n' if positive else None,
            read_errno=None if positive else control.errno.ENOENT,
            write_count=len('changed-'+label+'\n') if positive else None,
            write_errno=None if positive else control.errno.ENOENT,
            readback='changed-'+label+'\n' if positive else None))
    return dict(schema=1,targets=[str(p) for p in targets],uid=1000,workspace_control=True,cases=cases)


def policy(workspace,targets,positive,cid='a'*64,state='created'):
    argv=control.command(workspace,targets,positive,pathlib.Path('/private/cid'))
    bindings=[(str(workspace),'/workspace')]
    if positive:bindings.extend((str(p),str(p)) for p in targets)
    return argv,dict(id=cid,image=control.backend.IMAGE,entrypoint=['/usr/bin/env'],command=argv[argv.index(control.backend.IMAGE)+1:],
        user='1000:1000',mounts=[dict(Type='bind',Source=a,Destination=b,RW=True,Propagation='rprivate') for a,b in bindings],
        readonly=True,network='none',caps=['ALL'],security=['no-new-privileges'],restart={'Name':'no','MaximumRetryCount':0},
        pids=64,memory=536870912,cpus=1000000000,tmpfs={'/tmp':'rw,noexec,nosuid,size=32m,mode=1777'},
        privileged=False,pid_mode='',ipc_mode='private',userns_mode='',cgroupns_mode='private',devices=[],device_requests=None,
        volumes_from=None,state=state,running=False,pid=0,exit=0,oom=False)


class PathControlsTests(unittest.TestCase):
    def setUp(self):
        self.targets=[pathlib.Path('/private/fixed')/label for label in control.LABELS]
        self.workspace=pathlib.Path('/private/fixed/positive')

    def test_import_restores_search_path_without_engine_or_run(self):
        before=list(sys.path)
        with mock.patch.object(control.backend.subprocess,'check_output') as effect:
            module=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(module)
        self.assertEqual(sys.path,before);effect.assert_not_called()

    def test_same_program_targets_uid_and_policy_only_differ_in_canary_mounts(self):
        a=control.command(self.workspace,self.targets,True,pathlib.Path('/private/a'))
        b=control.command(self.workspace,self.targets,False,pathlib.Path('/private/b'))
        self.assertEqual(a[a.index(control.backend.IMAGE):],b[b.index(control.backend.IMAGE):])
        self.assertEqual(a.count('--mount'),4);self.assertEqual(b.count('--mount'),1)
        self.assertNotIn('Config.Env',control.FORMAT)

    def test_mount_source_destination_rw_extra_and_missing_are_rejected(self):
        for positive in (True,False):
            argv,good=policy(self.workspace,self.targets,positive)
            control.validate_policy(good,'a'*64,argv,self.workspace,self.targets,positive,'created')
            cases=[]
            for field,wrong in [('Source','/other'),('Destination','/other'),('RW',False),('Type','volume'),('Propagation','rshared')]:
                value=copy.deepcopy(good);value['mounts'][0][field]=wrong;cases.append(value)
            value=copy.deepcopy(good);value['mounts'].append(value['mounts'][0]);cases.append(value)
            value=copy.deepcopy(good);value['mounts'].pop();cases.append(value)
            for value in cases:
                with self.subTest(positive=positive),self.assertRaises(ValueError):control.validate_policy(value,'a'*64,argv,self.workspace,self.targets,positive,'created')

    def test_running_oom_exit_identity_user_and_policy_drift_are_rejected(self):
        argv,good=policy(self.workspace,self.targets,True,state='exited')
        for field,wrong in [('id','b'*64),('user','0:0'),('image','other'),('state','running'),('running',True),('pid',123),('oom',True),('exit',1),('network','default'),('privileged',True),('cgroupns_mode','host')]:
            value=copy.deepcopy(good);value[field]=wrong
            with self.subTest(field=field),self.assertRaises(ValueError):control.validate_policy(value,'a'*64,argv,self.workspace,self.targets,True,'exited')

    def test_empty_subset_duplicate_extra_wrong_targets_and_workspace_are_rejected(self):
        good=result(self.targets,True);control.validate_result(good,self.targets,True)
        cases=[]
        for rows in ([],good['cases'][:2],good['cases']+good['cases'][:1],[good['cases'][0]]*3):
            value=copy.deepcopy(good);value['cases']=rows;cases.append(value)
        for key,wrong in [('uid',0),('workspace_control',False),('schema',True),('targets',[])]:
            value=copy.deepcopy(good);value[key]=wrong;cases.append(value)
        value=copy.deepcopy(good);value['cases'][0]['target']='/other';cases.append(value)
        for value in cases:
            with self.assertRaises(ValueError):control.validate_result(value,self.targets,True)

    def test_read_success_without_write_or_readback_is_not_positive(self):
        for field,wrong in [('write_count',None),('write_errno',control.errno.EACCES),('readback','partial'),('read','partial')]:
            value=result(self.targets,True);value['cases'][0][field]=wrong
            with self.subTest(field=field),self.assertRaises(ValueError):control.validate_result(value,self.targets,True)

    def test_negative_requires_each_read_and_write_boundary_errno(self):
        control.validate_result(result(self.targets,False),self.targets,False)
        for field in ('read_errno','write_errno'):
            for invalid in (None,True,control.errno.EIO,control.errno.ENOMEM):
                value=result(self.targets,False);value['cases'][0][field]=invalid
                with self.subTest(field=field,invalid=invalid),self.assertRaises(ValueError):control.validate_result(value,self.targets,False)
        for positive in (True,False):
            with self.assertRaises(ValueError):control.validate_result(result(self.targets,not positive),self.targets,positive)

    def test_reset_refuses_mode_inode_symlink_hardlink_or_bytes_drift(self):
        for drift in ('mode','inode','symlink','hardlink','bytes'):
            with self.subTest(drift=drift),tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory).resolve();paths=[root/label for label in control.LABELS];ids=[]
                for label,path in zip(control.LABELS,paths,strict=True):
                    data=('changed-'+label+'\n').encode();path.write_bytes(data);path.chmod(0o666);ids.append(control.identity(path,data))
                p=paths[0]
                if drift=='mode':p.chmod(0o600)
                elif drift=='inode':other=root/'replacement';other.write_bytes(p.read_bytes());other.chmod(0o666);other.replace(p)
                elif drift=='symlink':p.unlink();p.symlink_to(paths[1])
                elif drift=='hardlink':(root/'alias').hardlink_to(p)
                else:p.write_bytes(b'partial')
                with self.assertRaises(ValueError):control.reset_canaries(paths,ids)
                self.assertEqual(paths[1].read_bytes(),b'changed-checkpoint\n')

    def test_reset_changes_only_original_synthetic_inodes_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory).resolve();paths=[root/label for label in control.LABELS];ids=[]
            for label,path in zip(control.LABELS,paths,strict=True):
                data=('changed-'+label+'\n').encode();path.write_bytes(data);path.chmod(0o666);ids.append(control.identity(path,data))
            control.reset_canaries(paths,ids)
            for label,path,expected in zip(control.LABELS,paths,ids,strict=True):self.assertEqual(control.identity(path,(label+'\n').encode()),expected)

    def test_unknown_positive_prevents_reset_and_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            parent=pathlib.Path(directory).resolve()
            with mock.patch.object(control.backend,'evidence_root',return_value=parent),mock.patch.object(control.backend,'LocalDesktop') as engine,mock.patch.object(control,'execute_phase',side_effect=OSError('unknown')) as execute,mock.patch.object(control,'reset_canaries') as reset:
                with self.assertRaises(OSError):control.run(str(parent))
                self.assertEqual(execute.call_count,1);self.assertIs(execute.call_args.args[4],True);reset.assert_not_called()

    def test_unknown_create_is_not_started_or_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory).resolve();engine=mock.Mock();engine.call.side_effect=control.subprocess.TimeoutExpired('docker',1)
            with self.assertRaises(control.subprocess.TimeoutExpired):control.execute_phase(engine,root,root/'workspace',self.targets,True)
            self.assertEqual(engine.call.call_count,1);self.assertEqual(engine.call.call_args.args[0][1],'create')
            recovery=json.loads((root/'positive-unknown.json').read_text());self.assertFalse(recovery['started']);self.assertFalse(recovery['replayed'])

    def test_unknown_start_does_not_replay_reset_or_launch_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            parent=pathlib.Path(directory).resolve();engine=mock.Mock();calls=[];created={}
            def dispatch(argv):
                calls.append(argv[1])
                if argv[1]=='info':return '00000000-1111-2222-3333-444444444444 linux'
                if argv[1]=='create':
                    cidfile=pathlib.Path(argv[argv.index('--cidfile')+1]);cidfile.write_text('a'*64+'\n')
                    workspace=cidfile.parent/'positive';targets=[cidfile.parent/label for label in control.LABELS]
                    _,created['policy']=policy(workspace,targets,True)
                    return 'a'*64
                if argv[1]=='inspect':return json.dumps(created['policy'])
                if argv[1]=='start':raise control.subprocess.TimeoutExpired('docker',1)
                self.fail('unexpected effect after unknown start')
            engine.call.side_effect=dispatch
            with mock.patch.object(control.backend,'evidence_root',return_value=parent),mock.patch.object(control.backend,'LocalDesktop',return_value=engine),mock.patch.object(control,'reset_canaries') as reset:
                with self.assertRaises(control.subprocess.TimeoutExpired):control.run(str(parent))
                self.assertEqual(calls,['info','create','inspect','start']);reset.assert_not_called()

    def test_reused_cid_never_starts_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory).resolve();(root/'negative-cid').write_text('a'*64+'\n');engine=mock.Mock();engine.call.return_value='a'*64
            with self.assertRaises(ValueError):control.execute_phase(engine,root,root/'workspace',self.targets,False,'a'*64)
            self.assertEqual(engine.call.call_count,1)


if __name__=='__main__':unittest.main()
