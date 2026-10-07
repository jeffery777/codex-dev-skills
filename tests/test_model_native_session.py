"""Native session evidence counterexamples; no Docker, CLI or real terminals."""
import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location('native_session_control',pathlib.Path(__file__).resolve().parents[1]/'scripts/verify-model-native-session.py')
control=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(control)
fixture=control.fixture

def native(body='',sid=12345):
    status='Process exited with code 0' if sid is None else 'Process running with session ID '+str(sid)
    return 'Chunk ID: 12abcd\nWall time: 1.0000 seconds\n'+status+'\nOriginal token count: 4\nOutput:\n'+body

def evidence(workspace,extra_poll=False,mode='tty'):
    sid=12345;error='write_stdin failed: Unknown process id '+str(sid)
    calls=[fixture.call(0,'exec_command',fixture.terminal(mode)),fixture.poll(1,sid),fixture.poll(2,sid,fixture.INPUT)]
    outputs=[native('SESSION_READY\n'),native()]
    if mode=='non-tty':
        outputs.extend([fixture.STDIN_CLOSED,native()]);calls.extend([fixture.poll(3,sid),fixture.poll(4,sid)])
        fixture.publish_release(workspace)
    outputs.append(native(('' if mode=='non-tty' else fixture.INPUT)+'SESSION_ACK\n',sid if extra_poll else None))
    if extra_poll:calls.append(fixture.poll(5 if mode=='non-tty' else 3,sid));outputs.append(native(sid=None))
    calls.append(fixture.poll(6 if mode=='non-tty' else 4,sid));outputs.append(error)
    functions=[{'type':'function','name':name,'parameters':{'type':'object'}} for name in ('exec_command','write_stdin')]
    tools=[{'type':'namespace','name':'functions','tools':[*functions,{'type':'custom','name':'apply_patch','format':{'type':'text'}}]}]
    def stream(calls,outputs):
        requests=[dict(model='fixture-direct',input=[],tools=copy.deepcopy(tools))]
        for call,output in zip(calls,outputs,strict=True):requests.append(dict(model='fixture-direct',input=[dict(type='function_call_output',call_id=call['call_id'],output=output)],tools=copy.deepcopy(tools)))
        return dict(calls=calls,outputs=outputs,requests=requests)
    (workspace/'session-marker').write_bytes(b'session-ack-control\n')
    paths=['/etc/codex/config.toml','/etc/codex/requirements.toml','/etc/codex/managed_config.toml','/config.toml','/.codex/config.toml','/workspace/config.toml','/workspace/.codex/config.toml',*[f'/tmp/session-home-{p}/{n}' for p in ('a','b') for n in ('config.toml','managed_config.toml','auth.json')]]
    return dict(schema=2,terminal_mode=mode,source_pin=fixture.SOURCE_PIN,production_qualified=False,native_session_qualified=False,errors=[],inventory=[dict(path=p,exists=False,symlink=False,canonical=True) for p in paths],
        streams={'a':stream(calls,outputs),'b':stream([fixture.poll('b',sid,fixture.OTHER_INPUT)],[error])},
        cli={phase:dict(argv=fixture.cli_argv(port),exit=0,stdout=json.dumps({'type':'thread.started','thread_id':thread})+'\n',stderr='') for phase,port,thread in [('a',12345,'10000000-0000-4000-8000-000000000001'),('b',23456,'10000000-0000-4000-8000-000000000002')]})

def rewrite_output(value,phase,index,output):
    row=value['streams'][phase];index%=len(row['outputs']);row['outputs'][index]=output;row['requests'][index+1]['input'][0]['output']=output

class NativeSessionTests(unittest.TestCase):
    def test_release_is_complete_before_final_path_becomes_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);link=fixture.os.link;observations=[]
            def publish(source,target,**kwargs):
                observations.append((target.exists(),source.read_bytes()));link(source,target,**kwargs)
            with mock.patch.object(fixture.os,'link',side_effect=publish):fixture.publish_release(root)
            self.assertEqual(observations,[(False,fixture.RELEASE)])
            self.assertEqual((root/'session-release').read_bytes(),fixture.RELEASE)

    def test_partial_stage_never_publishes_or_replays_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);flush=mock.Mock(side_effect=OSError('fixed write failure'))
            with mock.patch.object(fixture.os,'fsync',flush),mock.patch.object(fixture.os,'link') as link:
                with self.assertRaises(OSError):fixture.publish_release(root)
                link.assert_not_called();self.assertFalse((root/'session-release').exists())
                with self.assertRaises(FileExistsError):fixture.publish_release(root)
                link.assert_not_called()

    def test_existing_release_is_preserved_and_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);final=root/'session-release';final.write_bytes(b'existing')
            with self.assertRaises(FileExistsError):fixture.publish_release(root)
            self.assertEqual(final.read_bytes(),b'existing');self.assertEqual((root/'session-release-staged').read_bytes(),fixture.RELEASE)

    def test_non_tty_direct_and_one_final_poll_positive(self):
        for extra in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);checks=control.validate_evidence(evidence(root,extra,'non-tty'),root,'non-tty')
                self.assertTrue(checks['non_tty_input_rejected']);self.assertFalse(checks['input_sent_once']);self.assertTrue(checks['input_attempted_once']);self.assertEqual(checks['calls'],8 if extra else 7)

    def test_non_tty_closed_stdin_live_poll_and_no_echo_required(self):
        for index,output in [(2,native()),(2,fixture.STDIN_CLOSED+'\n'),(3,native(sid=None)),(3,native('SESSION_READY\n')),(3,native(sid=54321)),(4,native(fixture.INPUT+'SESSION_ACK\n',None))]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root,mode='non-tty');rewrite_output(v,'a',index,output)
                with self.assertRaises(ValueError):control.validate_evidence(v,root,'non-tty')

    def test_non_tty_mode_command_and_release_cannot_be_substituted(self):
        for mutate in [lambda v,r:v.update(terminal_mode='tty'),lambda v,r:v['streams']['a']['calls'][0].update(arguments=json.dumps(fixture.terminal('tty'))),lambda v,r:(r/'session-release').write_bytes(b'wrong'),lambda v,r:((r/'session-release').rename(r/'target'),(r/'session-release').symlink_to(r/'target')),lambda v,r:((r/'session-release-staged').rename(r/'original-stage'),(r/'session-release-staged').write_bytes(fixture.RELEASE))]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root,mode='non-tty');mutate(v,root)
                with self.assertRaises(ValueError):control.validate_evidence(v,root,'non-tty')
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);v=evidence(root)
            with self.assertRaises(ValueError):control.validate_evidence(v,root,'non-tty')
            (root/'session-release').write_bytes(fixture.RELEASE)
            with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_non_tty_every_ack_split_preserves_single_normalization(self):
        for raw,accepted in [('SESSION_ACK\r\n',True),('SESSION_ACK\r\r\n',False),(fixture.INPUT+'SESSION_ACK\n',False)]:
            for index in range(len(raw)+1):
                with self.subTest(raw=raw,index=index),tempfile.TemporaryDirectory() as directory:
                    root=pathlib.Path(directory);v=evidence(root,True,'non-tty');rewrite_output(v,'a',4,native(raw[:index]));rewrite_output(v,'a',5,native(raw[index:],None))
                    if accepted:self.assertTrue(control.validate_evidence(v,root,'non-tty')['non_tty_input_rejected'])
                    else:
                        with self.assertRaises(ValueError):control.validate_evidence(v,root,'non-tty')

    def test_unknown_mode_prevents_runtime_effects(self):
        for mode in (None,True,'other'):
            with mock.patch.object(control.backend,'capture_binary',side_effect=AssertionError('binary')),mock.patch('pathlib.Path.mkdir',side_effect=AssertionError('directory')):
                with self.assertRaises(ValueError):control.run('/unused','/private/tmp',mode)
                with self.assertRaises(ValueError):fixture.run_fixture(mode)

    def test_non_tty_command_is_fixed_suffix_only(self):
        args=[pathlib.Path('/binary'),pathlib.Path('/workspace'),pathlib.Path('/cid')]
        self.assertEqual(control.command(*args,mode='non-tty'),control.command(*args)+['non-tty'])

    def test_import_restores_path_and_has_no_runtime_or_signal_effect(self):
        before=list(sys.path)
        with mock.patch('subprocess.run',side_effect=AssertionError('CLI')),mock.patch('subprocess.check_output',side_effect=AssertionError('Docker')),mock.patch('signal.signal',side_effect=AssertionError('signal')),mock.patch('signal.alarm',side_effect=AssertionError('alarm')):SPEC.loader.exec_module(control)
        self.assertEqual(before,sys.path)

    def test_direct_and_one_final_poll_positive(self):
        for extra in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);checks=control.validate_evidence(evidence(root,extra),root)
                self.assertEqual(checks['sid'],12345);self.assertTrue(checks['input_sent_once']);self.assertEqual(checks['calls'],6 if extra else 5)

    def test_source_capture_is_same_guest_program_after_file_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);path=root/'source.py';path.write_text('VALUE="first"\n');loaded,program=control.support.load_fixture(path);path.write_text('VALUE="second"\n')
            self.assertEqual(loaded.VALUE,'first');self.assertEqual(control.command(root/'codex',root/'scratch',root/'cid',program)[-1],program)

    def test_partial_ack_and_crlf_across_chars_and_final_poll(self):
        for first,last in [('SESSION_','ACK\n'),('SESSION_ACK\r','\n'),('session-input-control\r','\nSESSION_ACK\r\n')]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root,True);rewrite_output(v,'a',2,native(first));rewrite_output(v,'a',3,native(last,None))
                self.assertTrue(control.validate_evidence(v,root)['input_sent_once'])

    def test_all_split_positions_preserve_raw_body_and_single_normalization(self):
        for raw,accepted in [('SESSION_ACK\r\n',True),(fixture.INPUT.replace('\n','\r\n')+'SESSION_ACK\r\n',True),('SESSION_ACK\r\r\n',False),(fixture.INPUT.replace('\n','\r\r\n')+'SESSION_ACK\r\n',False)]:
            for index in range(len(raw)+1):
                with self.subTest(raw=raw,index=index),tempfile.TemporaryDirectory() as directory:
                    root=pathlib.Path(directory);v=evidence(root,True);first,last=raw[:index],raw[index:]
                    self.assertEqual(fixture.parse_output(native(first))['body'],first)
                    rewrite_output(v,'a',2,native(first));rewrite_output(v,'a',3,native(last,None))
                    if accepted:self.assertTrue(control.validate_evidence(v,root)['input_sent_once'])
                    else:
                        with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_header_only_identity_ignores_body_fake_header(self):
        body='Process running with session ID 99999\n'
        self.assertEqual(fixture.parse_output(native(body))['sid'],12345)
        self.assertEqual(fixture.parse_output(native(body,sid=None))['status'],'exited')

    def test_unknown_carrier_header_exit_range_and_overflow_rejected(self):
        for raw in ([dict(type='input_text',text=native())],native().replace('Wall time: 1.0000','Wall time: NaN'),native(sid=999),native(sid=100000),native(sid=None).replace('code 0','code 1'),native('x'*4097),native().replace('Original token count: 4','Original token count: -1')):
            with self.assertRaises(ValueError):fixture.parse_output(raw)

    def test_wrong_run_id_sid_call_input_or_namespace_rejected(self):
        for mutate in [lambda v:v['streams']['a']['calls'][1].update(call_id='old-run'),lambda v:v['streams']['a']['calls'][1].update(arguments=json.dumps({'session_id':54321})),lambda v:v['streams']['a']['calls'][2].update(arguments=json.dumps({'session_id':12345,'chars':fixture.INPUT*2})),lambda v:v['streams']['b']['calls'][0].update(namespace='unconfigured')]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root);mutate(v)
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_ready_repetition_missing_ack_and_running_forever_rejected(self):
        for index,output,extra in [(1,native('SESSION_READY\n'),False),(0,native(''),False),(2,native('SESSION_ACK\nSESSION_ACK\n',None),False),(2,native('SESSION_ACK\n',54321),True),(3,native(''),True)]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root,extra);rewrite_output(v,'a',index,output)
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_cross_thread_and_post_exit_must_be_exact_unknown(self):
        for phase in ('a','b'):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root);rewrite_output(v,phase,-1,native(sid=None))
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_missing_duplicate_or_wrong_continuation_rejected(self):
        for variant in ('missing','duplicate','wrong'):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root);items=v['streams']['a']['requests'][1]['input']
                if variant=='missing':items.clear()
                elif variant=='duplicate':items.append(copy.deepcopy(items[0]))
                else:items[0]['output']='wrong'
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_thread_identity_missing_duplicate_reused_and_port_reuse_rejected(self):
        for mutate in [lambda v:v['cli']['a'].update(stdout=''),lambda v:v['cli']['a'].update(stdout=v['cli']['a']['stdout']*2),lambda v:v['cli']['b'].update(stdout=v['cli']['a']['stdout']),lambda v:v['cli']['b'].update(argv=v['cli']['a']['argv'])]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root);mutate(v)
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_argv_provider_and_extra_feature_rejected(self):
        for mutate in [lambda a:a.extend(['-c','features.hooks=true']),lambda a:a.__setitem__(a.index('--sandbox')+1,'read-only'),lambda a:a.__setitem__(a.index('--ignore-user-config'),'--dangerously-bypass-hook-trust')]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root);mutate(v['cli']['a']['argv'])
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_model_and_advertised_manifest_drift_rejected(self):
        for mutate in [lambda r:r.update(model='unconfigured'),lambda r:r['tools'][0]['tools'].pop(),lambda r:r['tools'][0]['tools'][0]['parameters'].update(additionalProperties=False)]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root);mutate(v['streams']['a']['requests'][1])
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_schema_startup_and_qualification_fail_closed(self):
        for mutate in [lambda v:v.update(schema=True),lambda v:v.update(schema=1),lambda v:v.update(production_qualified=True),lambda v:v.update(native_session_qualified=True),lambda v:v['inventory'][0].update(exists=True),lambda v:v['inventory'][0].update(exists=0),lambda v:v['cli']['a'].update(exit=True),lambda v:v.update(errors=['unknown'])]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root);mutate(v)
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_marker_drift_or_symlink_rejected(self):
        for symlink in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);v=evidence(root);marker=root/'session-marker'
                if symlink:marker.rename(root/'target');marker.symlink_to(root/'target')
                else:marker.write_text('wrong')
                with self.assertRaises(ValueError):control.validate_evidence(v,root)

    def test_unknown_create_is_recorded_and_never_started_or_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);engine=mock.Mock()
            def call(argv):
                if argv[1]=='create':(root/'cid').write_text('a'*64);raise subprocess.TimeoutExpired('create',55)
                return 'exact unknown state'
            engine.call.side_effect=call
            with mock.patch.object(control.backend,'check_binary'),self.assertRaises(subprocess.TimeoutExpired):control.execute(engine,root,root/'codex',root/'workspace')
            self.assertEqual([x.args[0][1] for x in engine.call.call_args_list],['create','inspect']);self.assertFalse(json.loads((root/'unknown-create.json').read_text())['replayed'])

    def test_unknown_start_has_exact_readback_and_never_waits(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);binary=root/'codex';workspace=root/'workspace';engine=mock.Mock();cid='a'*64
            def call(argv):
                if argv[1]=='create':(root/'cid').write_text(cid);return cid
                if argv[1]=='inspect':return '{}'
                raise subprocess.TimeoutExpired('start',55)
            engine.call.side_effect=call
            with mock.patch.object(control.backend,'check_binary'),mock.patch.object(control.support,'validate_policy'),self.assertRaises(subprocess.TimeoutExpired):control.execute(engine,root,binary,workspace)
            self.assertEqual([x.args[0][1] for x in engine.call.call_args_list],['create','inspect','start','inspect']);v=json.loads((root/'unknown-start.json').read_text());self.assertEqual(v['id'],cid);self.assertFalse(v['passed']);self.assertFalse(v['replayed'])

    def test_preexisting_layer_prevents_cli_and_provider(self):
        with mock.patch('pathlib.Path.exists',return_value=True),mock.patch('pathlib.Path.mkdir'),mock.patch('subprocess.run',side_effect=AssertionError('CLI')),mock.patch('http.server.ThreadingHTTPServer',side_effect=AssertionError('provider')):
            with self.assertRaises(ValueError):fixture.run_fixture()

if __name__=='__main__':unittest.main()
