"""Counterexamples for the fixed Docker recipe; no engine or provider calls."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import stat
import tempfile
import types
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('native_container_probe',
    pathlib.Path(__file__).resolve().parents[1]/'scripts/verify-model-container-native.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def receipt(workspace):
    calls,expectations=probe.fixture.fixed_cases()
    outputs=[]
    for expected in expectations:
        kind=expected['kind']
        if kind=='unsupported':
            outputs.append('unsupported call: '+(expected['namespace'] or '')+expected['name'])
        elif kind=='escalation-denied':
            outputs.append('approval policy is Never; reject command — you cannot ask for escalated permissions if the approval policy is Never')
        else:
            (workspace/expected['file']).write_text(expected['content'])
            outputs.append('Process exited with code 0\nOutput:\n' if kind in ('exec','exec-patch') else
                'Exit code: 0\nSuccess. Updated the following files:\nA '+expected['file'])
    requests=[{'model':'fixture-direct','input':[]}]
    for item,output in zip(calls,outputs,strict=True):
        kind='function_call_output' if item['type']=='function_call' else 'custom_tool_call_output'
        requests.append({'model':'fixture-direct','input':[{'type':kind,'call_id':item['call_id'],'output':output}]})
    return {'calls':calls,'expectations':expectations,'outputs':outputs,'requests':requests,'errors':[]}


class ContainerNativeTests(unittest.TestCase):
    def test_source_replacement_after_capture_does_not_change_mounted_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory).resolve();source=root/'source';data=b'fixed public binary'
            source.write_bytes(data)
            with mock.patch.object(probe,'BINARY_SHA256',hashlib.sha256(data).hexdigest()):
                captured=probe.capture_binary(str(source))
                source.write_bytes(b'replaced original')
                binary=probe.save_binary(root,captured)
                self.assertEqual(binary.read_bytes(),data)
                self.assertEqual(stat.S_IMODE(binary.stat().st_mode),0o555)
                probe.check_binary(binary)
                self.assertNotEqual(binary,source)
                binary.chmod(0o755)
                with self.assertRaises(ValueError):probe.check_binary(binary)

    def test_unverified_source_and_nonregular_descriptor_never_create_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory).resolve();source=root/'source';source.write_bytes(b'unverified')
            with self.assertRaises(ValueError):probe.capture_binary(str(source))
            with self.assertRaises(ValueError):probe.save_binary(root,b'unverified')
            self.assertFalse((root/'codex').exists())
            with mock.patch.object(probe.os,'fstat',return_value=types.SimpleNamespace(st_mode=stat.S_IFIFO,st_size=9)):
                with self.assertRaises(ValueError):probe.capture_binary(str(source))
            with mock.patch.object(probe,'BINARY_LIMIT',2):
                with self.assertRaises(ValueError):probe.capture_binary(str(source))
            alias=root/'alias';alias.symlink_to(source)
            with self.assertRaises(ValueError):probe.capture_binary(str(alias))

    def test_snapshot_content_and_hardlink_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory).resolve();data=b'fixed public binary'
            with mock.patch.object(probe,'BINARY_SHA256',hashlib.sha256(data).hexdigest()):
                binary=probe.save_binary(root,data)
                (root/'alias').hardlink_to(binary)
                with self.assertRaises(ValueError):probe.check_binary(binary)
                (root/'alias').unlink()
                binary.chmod(0o755);binary.write_bytes(b'different');binary.chmod(0o555)
                with self.assertRaises(ValueError):probe.check_binary(binary)

    def test_fixed_recipe_is_fresh_and_keeps_all_canonical_and_alternate_carriers(self):
        calls,expectations=probe.fixture.fixed_cases()
        self.assertEqual(len(calls),28)
        self.assertEqual(len(expectations),28)
        self.assertEqual([c['call_id'] for c in calls],['matrix-'+str(i) for i in range(28)])
        self.assertEqual([c.get('namespace') for c in calls[:8:2]],[None,None,'','functions'])
        self.assertNotIn('namespace',calls[0])
        self.assertIn('namespace',calls[2])
        for i,carrier in [(22,'apply_patch'),(23,'applypatch'),(24,'--codex-run-as-apply-patch'),(25,'/workspace/apply_patch'),(26,'/workspace/applypatch')]:
            self.assertIn(carrier,json.loads(calls[i]['arguments'])['cmd'])
        calls.clear();expectations.clear()
        self.assertEqual(len(probe.fixture.fixed_cases()[0]),28)

    def test_zero_subset_reorder_duplicate_and_rewritten_expectation_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            workspace=pathlib.Path(root);good=receipt(workspace)
            self.assertTrue(all(c['passed'] for c in probe.validate_cases(good,workspace)))
            empty={'calls':[],'expectations':[],'outputs':[],'requests':[{}]}
            cases=[empty]
            for key in ('calls','expectations','outputs','requests'):
                value=copy.deepcopy(good);value[key].pop();cases.append(value)
            value=copy.deepcopy(good);value['calls'].reverse();cases.append(value)
            value=copy.deepcopy(good);value['calls'][1]=value['calls'][0];cases.append(value)
            value=copy.deepcopy(good);value['expectations'][0]['file']='another';cases.append(value)
            for value in cases:
                with self.subTest(value=list(value)),self.assertRaises(ValueError):probe.validate_cases(value,workspace)

    def test_wrong_model_and_missing_duplicate_mismatched_continuations_cannot_pass(self):
        with tempfile.TemporaryDirectory() as root:
            workspace=pathlib.Path(root);good=receipt(workspace)
            cases=[]
            value=copy.deepcopy(good);value['requests'][0]['model']='different';cases.append(value)
            value=copy.deepcopy(good);value['requests'][1]['input']=[];cases.append(value)
            value=copy.deepcopy(good);value['requests'][1]['input']*=2;cases.append(value)
            for key,invalid in [('call_id','other'),('type','custom_tool_call_output'),('output','different')]:
                value=copy.deepcopy(good);value['requests'][1]['input'][0][key]=invalid;cases.append(value)
            for value in cases:
                with self.subTest(value=list(value)),self.assertRaises(ValueError):probe.validate_cases(value,workspace)

    def test_denial_uses_exact_protocol_namespace_display(self):
        with tempfile.TemporaryDirectory() as root:
            workspace=pathlib.Path(root);good=receipt(workspace)
            for wrong in ['unsupported call: collaboration.spawn_agent','unsupported call: spawn_agent','unsupported call: collaborationspawn_agent\n','error: unsupported call: collaborationspawn_agent']:
                value=copy.deepcopy(good);value['outputs'][16]=wrong;value['requests'][17]['input'][0]['output']=wrong
                with self.subTest(wrong=wrong):self.assertFalse(probe.validate_cases(value,workspace)[16]['passed'])

    def test_positive_file_drift_symlink_and_pending_process_are_not_success(self):
        with tempfile.TemporaryDirectory() as root:
            workspace=pathlib.Path(root);good=receipt(workspace)
            path=workspace/'scratch-exec-0';path.write_text('partial')
            self.assertFalse(probe.validate_cases(good,workspace)[0]['passed'])
            path.unlink();path.symlink_to(workspace/'scratch-exec-1')
            self.assertFalse(probe.validate_cases(good,workspace)[0]['passed'])
            value=copy.deepcopy(good);pending='Process exited with code 0\nProcess running with session ID 123'
            value['outputs'][2]=pending;value['requests'][3]['input'][0]['output']=pending
            self.assertFalse(probe.validate_cases(value,workspace)[2]['passed'])

    def test_unknown_and_oversized_typed_carriers_are_rejected(self):
        good=[{'type':'input_text','text':'Wall time: 0.0008 seconds\nOutput:'},{'type':'input_text','text':'exact'}]
        self.assertEqual(probe.text_output(good),'exact')
        for value in [[],list(reversed(good)),good+good[1:],[dict(good[0],text='unknown'),good[1]],[dict(good[0],text='Wall time: 35.0001 seconds\nOutput:'),good[1]],'x'*32769,[good[0],dict(good[1],text='x'*32769)]]:
            with self.subTest(value=type(value).__name__),self.assertRaises(ValueError):probe.text_output(value)

    def test_advertisement_drift_and_extra_tools_are_rejected(self):
        tools=[{'type':'function','name':name,'parameters':{'type':'object'}} for name in ('exec_command','write_stdin')]
        tools.append({'type':'custom','name':'apply_patch','format':{'type':'text'}})
        request={'input':[{'type':'additional_tools','role':'developer','tools':[{'type':'namespace','name':'functions','tools':tools}]}]}
        value={'requests':[copy.deepcopy(request) for _ in range(29)]}
        self.assertEqual(len(probe.advertised(value)),29)
        for mutation in ('empty','subset','extra','drift'):
            other=copy.deepcopy(value)
            if mutation=='empty':other['requests']=[]
            elif mutation=='subset':other['requests'].pop()
            elif mutation=='extra':other['requests'][2]['input'][0]['tools'][0]['tools'].append({'type':'function','name':'unexpected','parameters':{'type':'object'}})
            else:other['requests'][2]['input'][0]['tools'][0]['tools'][0]['description']='changed'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):probe.advertised(other)

    def test_non_mac_and_nonstandard_roots_fail_before_engine_calls(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(probe.sys,'platform','linux'),mock.patch.object(probe.subprocess,'check_output') as engine:
                with self.assertRaises(ValueError):probe.evidence_root(root)
                engine.assert_not_called()
            with mock.patch.object(probe.sys,'platform','darwin'):
                with self.assertRaises(ValueError):probe.evidence_root(root)

    def test_only_sticky_system_temporary_root_with_trusted_ancestors_is_allowed(self):
        def trusted(path):
            mode=stat.S_IFDIR|(0o1777 if str(path)=='/private/tmp' else 0o755)
            return types.SimpleNamespace(st_mode=mode,st_uid=0)
        def verify(path,info):
            with mock.patch.object(probe.sys,'platform','darwin'),mock.patch.object(probe.pathlib.Path,'resolve',return_value=pathlib.Path('/private/tmp')),mock.patch.object(probe.pathlib.Path,'lstat',autospec=True,side_effect=info),mock.patch.object(probe.pathlib.Path,'exists',return_value=False):
                return probe.evidence_root(path)
        self.assertEqual(verify('/private/tmp',trusted),pathlib.Path('/private/tmp'))
        for value in ('/tmp','/private/tmp/shared','/private/tmp/../tmp','relative'):
            with self.subTest(value=value),self.assertRaises(ValueError):verify(value,trusted)
        for mode,uid in [(stat.S_IFDIR|0o777,0),(stat.S_IFLNK|0o777,0),(stat.S_IFDIR|0o1777,1234)]:
            def invalid(path):
                if str(path)=='/private/tmp':return types.SimpleNamespace(st_mode=mode,st_uid=uid)
                return trusted(path)
            with self.subTest(mode=mode,uid=uid),self.assertRaises(ValueError):verify('/private/tmp',invalid)
        def writable_ancestor(path):
            if str(path)=='/private':return types.SimpleNamespace(st_mode=stat.S_IFDIR|0o777,st_uid=0)
            return trusted(path)
        with self.assertRaises(ValueError):verify('/private/tmp',writable_ancestor)
        with mock.patch.object(probe.sys,'platform','darwin'),mock.patch.object(probe.pathlib.Path,'resolve',return_value=pathlib.Path('/private/tmp')),mock.patch.object(probe.pathlib.Path,'lstat',autospec=True,side_effect=trusted),mock.patch.object(probe.pathlib.Path,'exists',return_value=True):
            with self.assertRaises(ValueError):probe.evidence_root('/private/tmp')

    def test_remote_same_named_context_is_rejected_without_daemon_connection(self):
        for endpoint in ('ssh://other','tcp://127.0.0.1:2375','unix:///another/socket',None):
            with self.subTest(endpoint=endpoint),mock.patch.object(probe.subprocess,'check_output',return_value=json.dumps(endpoint)) as run:
                with self.assertRaises(ValueError):probe.LocalDesktop()
                self.assertEqual(run.call_count,1)
                self.assertEqual(run.call_args.args[0][1:4],['context','inspect','desktop-linux'])
                self.assertNotIn('DOCKER_HOST',run.call_args.kwargs['env'])

    def test_transport_is_pinned_and_endpoint_or_socket_drift_precedes_effect(self):
        endpoint='unix:///fixed/socket';signature=(1,2,3,4)
        identity='00000000-1111-2222-3333-444444444444 linux'
        with mock.patch.object(probe,'local_endpoint',return_value=endpoint),mock.patch.object(probe,'socket_identity',return_value=signature),mock.patch.object(probe.subprocess,'check_output',return_value=identity) as run:
            engine=probe.LocalDesktop();self.assertEqual(engine.call(['docker','info']),identity)
            self.assertEqual(run.call_args.args[0][:3],['docker','--host',endpoint])
            run.reset_mock()
            with mock.patch.object(probe,'local_endpoint',return_value='unix:///changed/socket'):
                with self.assertRaises(ValueError):engine.call(['docker','create'])
            run.assert_not_called()

            with mock.patch.object(probe,'socket_identity',return_value=(1,999,3,4)):
                with self.assertRaises(ValueError):engine.call(['docker','start','a'*64])
            run.assert_not_called()

    def test_socket_requires_owned_canonical_socket_instead_of_regular_file_or_alias(self):
        expected=pathlib.Path('/fixed/.docker/run/docker.sock')
        def details(mode=stat.S_IFSOCK|0o700,uid=41):
            return types.SimpleNamespace(st_dev=1,st_ino=2,st_uid=uid,st_mode=mode)
        with mock.patch.object(probe.pathlib.Path,'home',return_value=pathlib.Path('/fixed')),mock.patch.object(probe.os,'getuid',return_value=41),mock.patch.object(probe.pathlib.Path,'resolve',return_value=expected):
            with mock.patch.object(probe.pathlib.Path,'lstat',return_value=details()):
                self.assertEqual(probe.socket_identity(),(1,2,41,stat.S_IFSOCK|0o700))
            for value in (details(mode=stat.S_IFREG|0o700),details(uid=42)):
                with self.subTest(value=value),mock.patch.object(probe.pathlib.Path,'lstat',return_value=value):
                    with self.assertRaises(ValueError):probe.socket_identity()
            with mock.patch.object(probe.pathlib.Path,'lstat',return_value=details()),mock.patch.object(probe.pathlib.Path,'resolve',return_value=pathlib.Path('/different')):
                with self.assertRaises(ValueError):probe.socket_identity()

    def test_engine_uuid_drift_precedes_create_and_start_and_unknown_identity_cannot_pass(self):
        endpoint='unix:///fixed/socket';signature=(1,2,3,4)
        first='00000000-1111-2222-3333-444444444444 linux'
        second='99999999-1111-2222-3333-444444444444 linux'
        for action in ('create','start'):
            with self.subTest(action=action),mock.patch.object(probe,'local_endpoint',return_value=endpoint),mock.patch.object(probe,'socket_identity',return_value=signature),mock.patch.object(probe.subprocess,'check_output',side_effect=[first,second]) as run:
                engine=probe.LocalDesktop();engine.call(['docker','info'])
                with self.assertRaises(ValueError):engine.call(['docker',action,'a'*64])
                self.assertEqual([call.args[0][3] for call in run.call_args_list],['info','info'])
        for value in ('','unknown','00000000-1111-2222-3333-444444444444 windows'):
            with self.subTest(value=value),mock.patch.object(probe,'local_endpoint',return_value=endpoint),mock.patch.object(probe,'socket_identity',return_value=signature),mock.patch.object(probe.subprocess,'check_output',return_value=value):
                with self.assertRaises(ValueError):probe.LocalDesktop().call(['docker','info'])


if __name__=='__main__':unittest.main()
