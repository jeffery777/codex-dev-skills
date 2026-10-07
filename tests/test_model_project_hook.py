"""Fixed project hook counterexamples; no Docker, CLI, hook or provider start."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location('project_hook_control',pathlib.Path(__file__).resolve().parents[1]/'scripts/verify-model-project-hook.py')
control=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(control)
fixture=control.fixture


def evidence(workspace,phase):
    project=workspace/'project';project.mkdir();(project/'.codex').mkdir()
    (project/'.codex/config.toml').write_text(fixture.project_config());(project/'tool-marker').write_bytes(b'project-tool-control\n')
    if phase=='positive':(project/'hook-marker.json').write_text(json.dumps({'hook_event_name':'PreToolUse','tool_name':'Bash','tool_input':{'command':fixture.TOOL_COMMAND}})+'\n')
    functions=[{'type':'function','name':name,'parameters':{'type':'object'}} for name in ('exec_command','write_stdin')]
    tools=[{'type':'namespace','name':'functions','tools':[*functions,{'type':'custom','name':'apply_patch','format':{'type':'text'}}]}]
    output='Process exited with code 0\nOutput:\n'
    return dict(schema=1,phase=phase,source_pin=fixture.SOURCE_PIN,production_qualified=False,
        startup_isolation_qualified=False,hook_trust_qualified=False,cli_exit=0,errors=[],
        call={'type':'function_call','namespace':'functions','name':'exec_command','call_id':'project-hook-0',
            'arguments':json.dumps({'cmd':fixture.TOOL_COMMAND,'login':False,'yield_time_ms':1000,'max_output_tokens':1000})},
        inventory=[dict(path=p,exists=False,symlink=False,canonical=True) for p in fixture.STARTUP_PATHS],
        project_config=fixture.project_config(),user_config=fixture.user_config(12345,phase),argv=fixture.cli_argv(),
        requests=[dict(model='fixture-direct',input=[],tools=tools),dict(model='fixture-direct',
            input=[dict(type='function_call_output',call_id='project-hook-0',output=output)],tools=copy.deepcopy(tools))],outputs=[output])


def policy(binary,workspace,phase,cidfile,state='created'):
    argv=control.command(binary,workspace,phase,cidfile)
    return dict(id='a'*64,image=control.backend.IMAGE,entrypoint=['/usr/bin/env'],command=argv[argv.index(control.backend.IMAGE)+1:],
        user='1000:1000',readonly=True,network='none',caps=['ALL'],security=['no-new-privileges'],
        restart={'Name':'no','MaximumRetryCount':0},pids=64,memory=536870912,cpus=1000000000,
        tmpfs={'/tmp':'rw,noexec,nosuid,size=32m,mode=1777'},privileged=False,pid_mode='',ipc_mode='private',
        userns_mode='',cgroupns_mode='private',devices=[],device_requests=None,volumes_from=None,
        state=state,running=False,pid=0,exit=0,oom=False,
        mounts=[dict(Type='bind',Source=str(binary),Destination='/fixture/codex',RW=False,Propagation='rprivate'),
            dict(Type='bind',Source=str(workspace),Destination='/workspace',RW=True,Propagation='rprivate')])


class ProjectHookTests(unittest.TestCase):
    def test_import_has_no_effect_and_restores_path(self):
        before=list(sys.path)
        with mock.patch('subprocess.check_output',side_effect=AssertionError('engine call')),mock.patch('subprocess.run',side_effect=AssertionError('CLI call')):SPEC.loader.exec_module(control)
        self.assertEqual(before,sys.path)

    def test_captured_source_binds_host_recipe_both_phases_and_hash_after_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);source=root/'fixture.py';raw=b'VALUE = "first"\n';source.write_bytes(raw)
            loaded,program=control.load_fixture(source);source.write_text('VALUE = "second"\n')
            self.assertEqual(loaded.VALUE,'first');self.assertEqual(program.encode(),raw)
            for phase in ('positive','negative'):
                argv=control.command(root/'codex',root/'workspace',phase,root/'cid',program)
                self.assertEqual(argv[-2],program)
            self.assertEqual(hashlib.sha256(program.encode()).hexdigest(),hashlib.sha256(raw).hexdigest())

    def test_fixture_source_symlink_nonregular_and_oversized_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);source=root/'fixture.py';source.write_text('VALUE=1\n');link=root/'link';link.symlink_to(source)
            with self.assertRaises(OSError):control.load_fixture(link)
            with self.assertRaises(OSError):control.load_fixture(root)
            source.write_bytes(b'X'*262145)
            with self.assertRaises(ValueError):control.load_fixture(source)

    def test_normalized_hook_identity_golden_hash_and_trust_layers(self):
        self.assertEqual(fixture.hook_hash(),'sha256:94fc2837760234c796bfa7978cdc036cdc0459c53a5e90a397fa4a9fb124ffdc')
        project=tomllib.loads(fixture.project_config());self.assertEqual(project['hooks']['state'][fixture.HOOK_KEY]['trusted_hash'],fixture.hook_hash())
        for phase in ('positive','negative'):
            user=tomllib.loads(fixture.user_config(12345,phase));self.assertTrue(user['features']['hooks'])
            self.assertEqual(user['hooks']['state'][fixture.HOOK_KEY]['trusted_hash'],fixture.hook_hash() if phase=='positive' else 'sha256:'+'0'*64)
        argv=fixture.cli_argv();self.assertNotIn('--dangerously-bypass-hook-trust',argv);self.assertNotIn('--ignore-user-config',argv);self.assertIn('--strict-config',argv)

    def test_loopback_port_and_phase_only(self):
        for port,phase in [(True,'positive'),(0,'positive'),(65536,'positive'),(1,'arbitrary')]:
            with self.assertRaises(ValueError):fixture.user_config(port,phase)

    def test_fixed_positive_and_modified_user_state_negative(self):
        for phase in ('positive','negative'):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);self.assertTrue(control.validate_evidence(evidence(root,phase),root,phase))

    def test_wrong_hook_event_tool_input_duplicate_and_missing_rejected(self):
        for drift in ('event','tool','command','duplicate','missing'):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);value=evidence(root,'positive');path=root/'project/hook-marker.json';payload=json.loads(path.read_text())
                if drift=='event':payload['hook_event_name']='PostToolUse'
                if drift=='tool':payload['tool_name']='exec_command'
                if drift=='command':payload['tool_input']['command']='printf wrong'
                if drift=='missing':path.unlink()
                else:path.write_text(json.dumps(payload)+'\n'+(json.dumps(payload)+'\n' if drift=='duplicate' else ''))
                with self.subTest(drift=drift),self.assertRaises((ValueError,FileNotFoundError)):control.validate_evidence(value,root,'positive')

    def test_negative_cannot_have_hook_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);value=evidence(root,'negative');(root/'project/hook-marker.json').write_text('{}')
            with self.assertRaises(ValueError):control.validate_evidence(value,root,'negative')

    def test_native_tool_positive_missing_bytes_or_symlink_is_not_pass(self):
        for drift in ('missing','bytes','symlink'):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);value=evidence(root,'negative');p=root/'project/tool-marker'
                if drift=='bytes':p.write_text('partial')
                else:
                    p.unlink()
                    if drift=='symlink':other=root/'other';other.write_bytes(b'project-tool-control\n');p.symlink_to(other)
                with self.assertRaises(ValueError):control.validate_evidence(value,root,'negative')

    def test_envelope_empty_subset_wrong_phase_or_qualification_rejected(self):
        for field,wrong in [('requests',[]),('outputs',[]),('phase','negative'),('schema',True),('cli_exit',True),('cli_exit',1),('errors',['unknown']),('production_qualified',True),('hook_trust_qualified',True)]:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);value=evidence(root,'positive');value[field]=wrong
                with self.subTest(field=field),self.assertRaises(ValueError):control.validate_evidence(value,root,'positive')

    def test_inventory_config_source_argv_or_destination_drift_rejected(self):
        mutations=[lambda v:v['inventory'].pop(),lambda v:v['inventory'][0].update(exists=True),lambda v:v['inventory'][0].update(exists=0),
            lambda v:v['inventory'][0].update(canonical=False),lambda v:v.update(project_config=''),
            lambda v:v['argv'].append('--dangerously-bypass-hook-trust'),lambda v:v.update(user_config=fixture.user_config(12345,'negative')),
            lambda v:v.update(user_config=v['user_config'].replace('127.0.0.1','external.invalid'))]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);value=evidence(root,'positive');mutate(value)
                with self.assertRaises(ValueError):control.validate_evidence(value,root,'positive')

    def test_native_call_continuation_or_running_result_drift_rejected(self):
        mutations=[lambda v:v['call'].update(call_id='wrong'),lambda v:v['requests'][1]['input'][0].update(call_id='wrong'),
            lambda v:v['requests'][1]['input'][0].update(output='wrong'),lambda v:v['outputs'].__setitem__(0,'Process running with session ID 3')]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);value=evidence(root,'positive');mutate(value)
                with self.assertRaises(ValueError):control.validate_evidence(value,root,'positive')

    def test_advertisement_missing_changed_or_unsupported_drift_rejected(self):
        mutations=[lambda v:v['requests'][1]['tools'][0]['tools'].pop(),
            lambda v:v['requests'][1]['tools'][0]['tools'][0].update(parameters={'type':'object','additionalProperties':False}),
            lambda v:v['requests'][0]['tools'][0]['tools'][0].update(name='shell')]
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);value=evidence(root,'positive');value['requests']=copy.deepcopy(value['requests']);mutate(value)
                with self.assertRaises(ValueError):control.validate_evidence(value,root,'positive')

    def test_policy_exact_image_uid_mount_rw_and_exit_required(self):
        binary=pathlib.Path('/private/own/codex');workspace=pathlib.Path('/private/own/scratch');cidfile=pathlib.Path('/private/own/cid')
        argv=control.command(binary,workspace,'positive',cidfile);good=policy(binary,workspace,'positive',cidfile,'exited')
        control.validate_policy(good,'a'*64,argv,binary,workspace,'exited')
        for field,wrong in [('id','b'*64),('image','other'),('oom',True),('running',True),('exit',1),('readonly',False),('pids',32),('network','host'),('cgroupns_mode','host')]:
            value=copy.deepcopy(good);value[field]=wrong
            with self.assertRaises(ValueError):control.validate_policy(value,'a'*64,argv,binary,workspace,'exited')
        value=copy.deepcopy(good);value['mounts'][0]['RW']=True
        with self.assertRaises(ValueError):control.validate_policy(value,'a'*64,argv,binary,workspace,'exited')

    def test_unknown_create_only_exact_readback_and_no_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);engine=mock.Mock()
            def call(argv):
                if argv[1]=='create':(root/'positive-cid').write_text('a'*64);raise subprocess.TimeoutExpired('create',55)
                return 'exact unknown created'
            engine.call.side_effect=call
            with mock.patch.object(control.backend,'check_binary'),self.assertRaises(subprocess.TimeoutExpired):control.execute(engine,root,root/'codex',root/'scratch','positive')
            self.assertEqual([c.args[0][1] for c in engine.call.call_args_list],['create','inspect'])
            self.assertFalse(json.loads((root/'positive-unknown-create.json').read_text())['replayed'])

    def test_unknown_start_records_exact_cid_no_wait_or_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);binary=root/'codex';workspace=root/'scratch';engine=mock.Mock()
            def call(argv):
                if argv[1]=='create':(root/'positive-cid').write_text('a'*64);return 'a'*64
                if argv[1]=='inspect':return json.dumps(policy(binary,workspace,'positive',root/'positive-cid'))
                raise subprocess.TimeoutExpired('start',55)
            engine.call.side_effect=call
            with mock.patch.object(control.backend,'check_binary'),self.assertRaises(subprocess.TimeoutExpired):control.execute(engine,root,binary,workspace,'positive')
            self.assertEqual([c.args[0][1] for c in engine.call.call_args_list],['create','inspect','start','inspect'])
            receipt=json.loads((root/'positive-unknown-start.json').read_text());self.assertEqual(receipt['id'],'a'*64);self.assertFalse(receipt['passed']);self.assertFalse(receipt['replayed'])

    def test_unknown_positive_never_launches_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory)
            with mock.patch.object(control.backend,'evidence_root',return_value=root),mock.patch.object(control.backend,'capture_binary',return_value=b'public'),mock.patch.object(control.backend,'save_binary',return_value=root/'codex'),mock.patch.object(control.backend,'LocalDesktop'),mock.patch.object(control,'execute',side_effect=ValueError('unknown')) as run:
                with self.assertRaises(ValueError):control.run('/fixed/public','/private/tmp')
                self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.args[4],'positive')

    def test_preexisting_startup_layer_stops_before_cli_or_provider(self):
        with mock.patch('pathlib.Path.exists',return_value=True),mock.patch('subprocess.run',side_effect=AssertionError('CLI executed')),mock.patch('http.server.ThreadingHTTPServer',side_effect=AssertionError('provider started')):
            with self.assertRaises(ValueError):fixture.run_fixture('positive')

    def test_reused_phase_cid_never_starts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);engine=mock.Mock()
            def call(argv):(root/'negative-cid').write_text('a'*64);return 'a'*64
            engine.call.side_effect=call
            with mock.patch.object(control.backend,'check_binary'),self.assertRaises(ValueError):control.execute(engine,root,root/'codex',root/'scratch','negative','a'*64)
            self.assertEqual([c.args[0][1] for c in engine.call.call_args_list],['create'])


if __name__=='__main__':unittest.main()
