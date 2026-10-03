"""PID-control counterexamples; never fork or exhaust host processes."""
import copy
import errno
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location('pid_control',pathlib.Path(__file__).resolve().parents[1]/'scripts/verify-model-isolation-pid-limit.py')
control=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(control)


def snapshot(current,events=0):
    return dict(cgroup='0::/',maximum=32,current=current,events=events,local_events=events)


def result():
    def row(count,events,failure):
        children=list(range(2,count+2))
        return dict(attempts=count+(failure is not None),children=children,ready=count,failure=failure,
            peak=snapshot(count+1,events),waited=[dict(pid=pid,status=0) for pid in children],after=snapshot(1,events))
    return dict(schema=1,pid=1,uid=1000,task_count=1,baseline=snapshot(1),positive=row(1,0,None),limited=row(31,1,control.LINUX_EAGAIN))


def policy(cidfile,state='created'):
    argv=control.command(cidfile)
    return dict(id='a'*64,image=control.backend.IMAGE,entrypoint=['/usr/bin/env'],command=argv[argv.index(control.backend.IMAGE)+1:],
        user='1000:1000',mounts=[],readonly=True,network='none',caps=['ALL'],security=['no-new-privileges'],
        restart={'Name':'no','MaximumRetryCount':0},pids=32,memory=536870912,cpus=1000000000,
        tmpfs={'/tmp':'rw,noexec,nosuid,size=32m,mode=1777'},privileged=False,pid_mode='',ipc_mode='private',
        userns_mode='',cgroupns_mode='private',devices=[],device_requests=None,volumes_from=None,
        state=state,running=False,pid=0,exit=0,oom=False)


class PidLimitTests(unittest.TestCase):
    def test_import_has_no_engine_effect_and_restores_path(self):
        before=list(sys.path)
        with mock.patch('subprocess.check_output',side_effect=AssertionError('engine call')):SPEC.loader.exec_module(control)
        self.assertEqual(before,sys.path)

    def test_fixed_profile_no_host_mounts_and_explicit_deadline(self):
        argv=control.command(pathlib.Path('/private/own/cid'))
        self.assertNotIn('--mount',argv);self.assertIn('--pids-limit=32',argv)
        self.assertIn('--pull=never',argv);self.assertIn('--restart=no',argv)
        self.assertIn('signal.signal(signal.SIGALRM,deadline)',control.PROGRAM)
        self.assertIn('os._exit(124)',control.PROGRAM)

    def test_success_requires_both_positive_and_enforcement_receipts(self):
        control.validate_result(result())
        value=result();value['positive']['children']=[]
        with self.assertRaises(ValueError):control.validate_result(value)

    def test_fixed_linux_errno_survives_json_and_rejects_macos_errno(self):
        value=result();self.assertEqual(value['limited']['failure'],11)
        control.validate_result(json.loads(json.dumps(value)))
        value['limited']['failure']=35
        with self.assertRaises(ValueError):control.validate_result(value)

    def test_errno_alone_missing_current_or_local_event_is_not_pass(self):
        for phase,key,wrong in [('limited','current',31),('limited','events',0),('limited','local_events',0),('positive','events',1),('positive','current',1)]:
            value=result();value[phase]['peak'][key]=wrong
            with self.subTest(phase=phase,key=key),self.assertRaises(ValueError):control.validate_result(value)

    def test_wrong_membership_maximum_negative_or_boolean_counters_rejected(self):
        for field,wrong in [('cgroup','0::/other'),('maximum',64),('maximum',True),('current',True),('events',-1),('local_events',10**19),('events',True)]:
            value=result();value['baseline'][field]=wrong
            with self.subTest(field=field),self.assertRaises(ValueError):control.validate_result(value)

    def test_wait_missing_wrong_pid_nonzero_duplicate_and_excess_children_rejected(self):
        mutations=[lambda r:r['waited'].pop(),lambda r:r['waited'][0].update(pid=999),lambda r:r['waited'][0].update(status=9),
            lambda r:r['children'].__setitem__(1,r['children'][0]),lambda r:r['children'].append(99),lambda r:r.update(attempts=33),lambda r:r.update(ready=30),lambda r:r.update(failure=errno.ENOMEM)]
        for mutate in mutations:
            value=result();mutate(value['limited'])
            with self.assertRaises(ValueError):control.validate_result(value)

    def test_counter_rollback_late_event_and_unreaped_children_rejected(self):
        for field,wrong in [('current',2),('events',0),('local_events',2)]:
            value=result();value['limited']['after'][field]=wrong
            with self.subTest(field=field),self.assertRaises(ValueError):control.validate_result(value)

    def test_wrong_uid_pid_schema_or_extra_result_rejected(self):
        for field,wrong in [('uid',0),('pid',2),('pid',True),('task_count',2),('task_count',True),('schema',True),('extra','unknown')]:
            value=result();value[field]=wrong
            with self.assertRaises(ValueError):control.validate_result(value)

    def test_policy_rejects_mounts_oom_running_wrong_limit_and_host_namespaces(self):
        cidfile=pathlib.Path('/private/own/cid');good=policy(cidfile,'exited');argv=control.command(cidfile)
        control.validate_policy(good,'a'*64,argv,'exited')
        for field,wrong in [('mounts',[{'Type':'bind'}]),('pids',64),('oom',True),('running',True),('exit',124),('pid_mode','host'),('cgroupns_mode','host'),('privileged',True),('network','host'),('id','b'*64),('memory',True)]:
            value=copy.deepcopy(good);value[field]=wrong
            with self.subTest(field=field),self.assertRaises(ValueError):control.validate_policy(value,'a'*64,argv,'exited')

    def test_guest_batch_is_bounded_and_closes_writer_before_wait_even_after_fork_error(self):
        namespace={'__name__':'offline_guest'};exec(control.PROGRAM,namespace)
        fake=mock.Mock();fake.pipe.side_effect=[(70,71),(72,73)];fake.read.return_value=b'R';fake.fork.side_effect=[2,3,OSError(errno.EAGAIN,'bounded')]
        fake.waitpid.side_effect=[(2,0),(3,0)]
        namespace['os']=fake;namespace['snapshot']=mock.Mock(side_effect=[snapshot(3,1),snapshot(1,1)])
        row=namespace['batch'](32)
        self.assertEqual(row['attempts'],3);self.assertEqual(row['failure'],errno.EAGAIN)
        self.assertEqual(fake.fork.call_count,3)
        self.assertEqual(fake.method_calls[-6:],[mock.call.close(71),mock.call.close(70),mock.call.close(73),mock.call.close(72),mock.call.waitpid(2,0),mock.call.waitpid(3,0)])

    def test_guest_batch_stops_at_fixed_limit_and_cleanup_on_snapshot_error(self):
        for broken in (False,True):
            namespace={'__name__':'offline_guest'};exec(control.PROGRAM,namespace)
            fake=mock.Mock();fake.pipe.side_effect=[(70,71),(72,73)];fake.read.return_value=b'R';fake.fork.side_effect=range(2,34)
            fake.waitpid.side_effect=[(pid,0) for pid in range(2,34)];namespace['os']=fake
            namespace['snapshot']=mock.Mock(side_effect=ValueError('unknown') if broken else [snapshot(33),snapshot(1)])
            if broken:
                with self.assertRaises(ValueError):namespace['batch'](32)
            else:self.assertEqual(len(namespace['batch'](32)['children']),32)
            self.assertEqual(fake.fork.call_count,32);self.assertEqual(fake.waitpid.call_count,32)
            fake.close.assert_any_call(71);fake.close.assert_any_call(70)

    def test_guest_child_closes_inherited_writer_before_read_and_exits(self):
        namespace={'__name__':'offline_guest'};exec(control.PROGRAM,namespace)
        fake=mock.Mock();fake.pipe.side_effect=[(70,71),(72,73)];fake.fork.return_value=0;fake.read.return_value=b'';fake._exit.side_effect=SystemExit(0);namespace['os']=fake
        with self.assertRaises(SystemExit):namespace['batch'](1)
        self.assertEqual(fake.method_calls[3:9],[mock.call.close(71),mock.call.close(72),mock.call.write(73,b'R'),mock.call.close(73),mock.call.read(70,1),mock.call._exit(0)])

    def test_guest_child_read_exception_or_non_eof_is_failure(self):
        for response in (OSError(errno.EIO,'unknown'),b'X'):
            namespace={'__name__':'offline_guest'};exec(control.PROGRAM,namespace)
            fake=mock.Mock();fake.pipe.side_effect=[(70,71),(72,73)];fake.fork.return_value=0
            if isinstance(response,Exception):fake.read.side_effect=response
            else:fake.read.return_value=response
            fake._exit.side_effect=lambda code:(_ for _ in ()).throw(SystemExit(code));namespace['os']=fake
            with self.assertRaises(SystemExit) as raised:namespace['batch'](1)
            self.assertEqual(raised.exception.code,125);fake._exit.assert_called_once_with(125)

    def test_guest_counter_readers_reject_missing_unbounded_or_unknown_formats(self):
        namespace={'__name__':'offline_guest'};exec(control.PROGRAM,namespace)
        for body in (b'max\n',b'-1\n',b'1\nextra',b'9'*513):
            with mock.patch('builtins.open',mock.mock_open(read_data=body)),self.assertRaises(ValueError):namespace['number']('pids.max')
        for body in (b'max 1\nother 0\n',b'max -1\n',b'',b'x'*513):
            with mock.patch('builtins.open',mock.mock_open(read_data=body)),self.assertRaises(ValueError):namespace['events']('pids.events.local')
        with mock.patch('builtins.open',side_effect=FileNotFoundError),self.assertRaises(FileNotFoundError):namespace['snapshot']()

    def test_guest_positive_mismatch_stops_before_limit_batch(self):
        namespace={'__name__':'offline_guest'};exec(control.PROGRAM,namespace)
        value=result()['positive'];value['peak']['current']=1
        fake=mock.Mock();fake.getpid.return_value=1;fake.getuid.return_value=1000;namespace['os']=fake
        namespace['signal']=mock.Mock();namespace['pathlib']=mock.Mock()
        namespace['pathlib'].Path.return_value.iterdir.return_value=[object()]
        namespace['snapshot']=mock.Mock(return_value=snapshot(1));namespace['batch']=mock.Mock(return_value=value)
        with self.assertRaises(ValueError):namespace['main']()
        namespace['batch'].assert_called_once_with(1)
        namespace['signal'].alarm.assert_called_once_with(30)

    def test_guest_deadline_is_failure_even_for_pid1(self):
        namespace={'__name__':'offline_guest'};exec(control.PROGRAM,namespace)
        fake=mock.Mock();fake._exit.side_effect=SystemExit(124);namespace['os']=fake
        with self.assertRaises(SystemExit) as raised:namespace['deadline'](14,None)
        self.assertEqual(raised.exception.code,124);fake._exit.assert_called_once_with(124)

    def test_host_complete_chain_exact_policy_and_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);engine=mock.Mock()
            def call(argv):
                if argv[1]=='create':(root/'container-id').write_text('a'*64);return 'a'*64
                if argv[1]=='inspect':return json.dumps(policy(root/'container-id','exited' if (root/'before.json').exists() else 'created'))
                if argv[1]=='start':return 'a'*64
                if argv[1]=='wait':return '0'
                if argv[1]=='logs':return json.dumps(result())
                raise AssertionError('unexpected command')
            engine.call.side_effect=call
            cid,value=control.execute(engine,root);self.assertEqual(cid,'a'*64);control.validate_result(value)
            self.assertEqual([c.args[0][1] for c in engine.call.call_args_list],['create','inspect','start','wait','inspect','logs'])

    def test_unknown_create_only_inspects_exact_cid_and_never_starts_or_replays(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);engine=mock.Mock()
            def call(argv):
                if argv[1]=='create':
                    (root/'container-id').write_text('a'*64);raise subprocess.TimeoutExpired('create',55)
                return 'exact uncertain created'
            engine.call.side_effect=call
            with self.assertRaises(subprocess.TimeoutExpired):control.execute(engine,root)
            self.assertEqual([c.args[0][1] for c in engine.call.call_args_list],['create','inspect'])
            receipt=json.loads((root/'unknown-create.json').read_text());self.assertFalse(receipt['replayed']);self.assertFalse(receipt['started'])

    def test_unknown_start_no_wait_logs_or_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);engine=mock.Mock()
            def call(argv):
                if argv[1]=='create':(root/'container-id').write_text('a'*64);return 'a'*64
                if argv[1]=='inspect':return json.dumps(policy(root/'container-id'))
                raise subprocess.TimeoutExpired('start',55)
            engine.call.side_effect=call
            with self.assertRaises(subprocess.TimeoutExpired):control.execute(engine,root)
            self.assertEqual([c.args[0][1] for c in engine.call.call_args_list],['create','inspect','start','inspect'])
            receipt=json.loads((root/'unknown-start.json').read_text())
            self.assertEqual(receipt['id'],'a'*64);self.assertFalse(receipt['replayed']);self.assertFalse(receipt['passed'])
            self.assertEqual(json.loads((root/'start-intent.json').read_text())['id'],'a'*64)

    def test_start_cid_mismatch_records_unknown_without_wait_or_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);engine=mock.Mock()
            def call(argv):
                if argv[1]=='create':(root/'container-id').write_text('a'*64);return 'a'*64
                if argv[1]=='inspect':return json.dumps(policy(root/'container-id'))
                if argv[1]=='start':return 'b'*64
                raise AssertionError('unexpected effect')
            engine.call.side_effect=call
            with self.assertRaises(ValueError):control.execute(engine,root)
            self.assertEqual([c.args[0][1] for c in engine.call.call_args_list],['create','inspect','start','inspect'])
            receipt=json.loads((root/'unknown-start.json').read_text());self.assertEqual(receipt['error_type'],'CIDMismatch')
            self.assertFalse(receipt['passed']);self.assertFalse(receipt['replayed'])


if __name__=='__main__':unittest.main()
