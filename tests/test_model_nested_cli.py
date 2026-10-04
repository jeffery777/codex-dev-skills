"""Nested evidence counterexamples; unit tests never launch CLI or Docker."""
import copy
import errno
import importlib.util
import json
import pathlib
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location('nested_control',pathlib.Path(__file__).resolve().parents[1]/'scripts/verify-model-nested-cli.py')
control=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(control)
fixture=control.fixture

def native(body='',sid=None):
    status='Process exited with code 0' if sid is None else 'Process running with session ID '+str(sid)
    return 'Chunk ID: abc123\nWall time: 1.0000 seconds\n'+status+'\nOriginal token count: 4\nOutput:\n'+body

def evidence(root):
    root=root.resolve(strict=True)
    workspace=root/'workspace';workspace.mkdir();canaries=control.create_canaries(root)
    fixture.write_json(workspace/'canary-paths.json',[x['path'] for x in canaries]);fixture.publish_release(workspace)
    ports={'parent':12345,'positive':23456,'negative':34567};sid=45678
    threads={p:'10000000-0000-4000-8000-00000000000'+str(i+1) for i,p in enumerate(fixture.PHASES)}
    native_env={'CODEX_THREAD_ID':threads['parent'],'CODEX_SESSION_ID':'20000000-0000-4000-8000-000000000001','CODEX_VERSION':'0.159.3','CODEX_PERMISSION_PROFILE':None}
    observed={'schema':1,'source_pin':fixture.SOURCE_PIN,'phase':'parent','call_id':'nested-parent-0','marker_matches':True,'marker':fixture.MARKER,'home':str(fixture.home('parent')),'codex_home':str(fixture.home('parent')),'native':native_env,'keys':sorted(fixture.ENV_KEYS+['CODEX_THREAD_ID','CODEX_SESSION_ID','CODEX_VERSION'])}
    fixture.write_json(workspace/'wrapper-environment.json',observed)
    tools=[{'type':'namespace','name':'functions','tools':[*[{'type':'function','name':n,'parameters':{'type':'object'}} for n in ('exec_command','write_stdin')],{'type':'custom','name':'apply_patch','format':{'type':'text'}}]}]
    streams={}
    for phase in fixture.PHASES:
        work=workspace if phase=='parent' else workspace/phase
        if phase!='parent':work.mkdir()
        argv=fixture.cli_argv(ports[phase],phase);timeout=35 if phase=='parent' else 12
        fixture.write_json(work/(phase+'-cli.json'),{'argv':argv,'exit':0,'elapsed':1.0,'timeout':timeout})
        environment={k:observed[k] for k in ('home','codex_home','marker','native','keys')}
        environment.update(home=str(fixture.home(phase)),codex_home=str(fixture.home(phase)))
        if phase=='parent':environment={'home':str(fixture.home('parent')),'codex_home':str(fixture.home('parent')),'marker':fixture.MARKER,'native':dict.fromkeys(fixture.NATIVE_KEYS),'keys':sorted(fixture.ENV_KEYS)}
        fixture.write_json(work/(phase+'-spawn-intent.json'),{'argv':argv,'replayed':False,'timeout':timeout,'environment':environment})
        (work/(phase+'-stdout.jsonl')).write_text(json.dumps({'type':'thread.started','thread_id':threads[phase]})+'\n');(work/(phase+'-stderr.txt')).write_text('')
        if phase=='parent':calls=[fixture.exec_call(phase),fixture.poll(phase,1,sid)];outputs=[native('NESTED_READY\n',sid),native('NESTED_ACK\n')]
        else:
            fixture.write_json(work/'user-config.json',{'path':str(fixture.home(phase)/'config.toml'),'content':fixture.config()})
            result={'phase':phase,'marker':fixture.MARKER if phase=='positive' else None,'marker_matches':True,'thread_env':threads[phase],'scratch':True,'attempts':[dict(path=x['path'],operation=op,outcome='denied') for x in canaries for op in ('read','write')]}
            fixture.write_json(work/'probe.json',result);(work/'probe-marker').write_bytes(b'fixed-nested-probe\n')
            (work/'probe-observations.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in [control.observation_header(phase,result['marker'],threads[phase]),{'scratch':True},*result['attempts']]))
            calls=[fixture.poll(phase,0,sid),fixture.exec_call(phase)];outputs=['write_stdin failed: Unknown process id '+str(sid),native(json.dumps(result)+'\n')]
        requests=[dict(model=fixture.model(phase),input=[],tools=copy.deepcopy(tools))]
        for call,output in zip(calls,outputs,strict=True):requests.append(dict(model=fixture.model(phase),input=[dict(type='function_call_output',call_id=call['call_id'],output=output)],tools=copy.deepcopy(tools)))
        row={'calls':calls,'outputs':outputs,'requests':requests,'errors':[]};streams[phase]=row;fixture.write_json(work/(phase+'-stream.json'),row)
    value={'schema':1,'source_pin':fixture.SOURCE_PIN,'inventory':[dict(path=p,exists=False,symlink=False,canonical=True) for p in fixture.startup_paths()],'streams':streams,'ports':ports,'handler_inventory_complete':False,'startup_isolation_qualified':False,'nested_cli_qualified':False,'production_qualified':False}
    return value,workspace,canaries

def overwrite(path,value):path.write_text(json.dumps(value)+'\n')
def sync_stream(value,workspace,phase):overwrite((workspace if phase=='parent' else workspace/phase)/(phase+'-stream.json'),value['streams'][phase])
def output(value,workspace,phase,index,text):
    row=value['streams'][phase];row['outputs'][index]=text;row['requests'][index+1]['input'][0]['output']=text;sync_stream(value,workspace,phase)

class NestedCliTests(unittest.TestCase):
    def test_import_has_no_cli_docker_signal_effect_and_restores_path(self):
        before=list(sys.path)
        with mock.patch('subprocess.run',side_effect=AssertionError('CLI')),mock.patch('subprocess.check_output',side_effect=AssertionError('Docker')),mock.patch('signal.signal',side_effect=AssertionError('signal')):SPEC.loader.exec_module(control)
        self.assertEqual(before,sys.path)

    def test_fixed_recipe_positive_and_false_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            value,work,rows=evidence(pathlib.Path(directory));result=control.validate_evidence(value,work,rows)
            self.assertTrue(result['fixed_nested_cli_controls_passed']);self.assertEqual(len(set(result['cli_threads'])),3)

    def test_child_completion_without_actual_tool_cycle_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            value,work,rows=evidence(pathlib.Path(directory));value['streams']['positive']['calls'].pop();sync_stream(value,work,'positive')
            with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_child_cannot_borrow_parent_identity(self):
        for kind in ('thread','port','output'):
            with tempfile.TemporaryDirectory() as directory:
                value,work,rows=evidence(pathlib.Path(directory))
                if kind=='thread':(work/'positive/positive-stdout.jsonl').write_bytes((work/'parent-stdout.jsonl').read_bytes())
                elif kind=='port':value['ports']['positive']=value['ports']['parent']
                else:output(value,work,'positive',1,value['streams']['parent']['outputs'][1])
                with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_missing_duplicate_wrong_or_cross_phase_continuation_rejected(self):
        for kind in ('missing','duplicate','wrong','cross-phase'):
            with tempfile.TemporaryDirectory() as directory:
                value,work,rows=evidence(pathlib.Path(directory));items=value['streams']['positive']['requests'][1]['input']
                if kind=='missing':items.clear()
                elif kind=='duplicate':items.append(copy.deepcopy(items[0]))
                elif kind=='wrong':items[0]['output']='wrong'
                else:items[0]['call_id']='nested-parent-0'
                sync_stream(value,work,'positive')
                with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_actual_config_model_and_environment_controls_rejected_on_drift(self):
        for phase in ('positive','negative'):
            for kind in ('config','model','marker','scratch','thread-env'):
                with tempfile.TemporaryDirectory() as directory:
                    value,work,rows=evidence(pathlib.Path(directory));child=work/phase
                    if kind=='config':overwrite(child/'user-config.json',{'path':str(fixture.home(phase)/'config.toml'),'content':'model="wrong"\n'})
                    elif kind=='model':value['streams'][phase]['requests'][1]['model']='wrong';sync_stream(value,work,phase)
                    elif kind=='scratch':(child/'probe-marker').write_bytes(b'wrong')
                    else:
                        result=fixture.read_json(child/'probe.json');result['marker' if kind=='marker' else 'thread_env']='wrong';overwrite(child/'probe.json',result);output(value,work,phase,1,native(json.dumps(result)))
                    with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_wrapper_guard_stripping_marker_injection_and_unknown_keys_rejected(self):
        for kind in ('strip','marker','unknown'):
            with tempfile.TemporaryDirectory() as directory:
                value,work,rows=evidence(pathlib.Path(directory));intent=fixture.read_json(work/'positive/positive-spawn-intent.json')
                if kind=='strip':intent['environment']['native']['CODEX_THREAD_ID']=None
                elif kind=='marker':intent['environment']['marker']='injected'
                else:intent['environment']['keys'].append('UNKNOWN_GUARD')
                overwrite(work/'positive/positive-spawn-intent.json',intent)
                with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_canary_attempts_and_host_drift_rejected(self):
        for kind in ('read','write','missing','host'):
            with tempfile.TemporaryDirectory() as directory:
                value,work,rows=evidence(pathlib.Path(directory))
                if kind=='host':pathlib.Path(rows[0]['path']).write_bytes(b'changed')
                else:
                    result=fixture.read_json(work/'positive/probe.json')
                    if kind=='missing':result['attempts'].pop()
                    else:result['attempts'][0 if kind=='read' else 1]['outcome']='opened'
                    overwrite(work/'positive/probe.json',result);output(value,work,'positive',1,native(json.dumps(result)))
                with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_unknown_spawn_timeout_truncation_and_fake_exit_rejected(self):
        for kind in ('intent','deadline','truncated','fake-exit'):
            with tempfile.TemporaryDirectory() as directory:
                value,work,rows=evidence(pathlib.Path(directory));child=work/'positive'
                if kind=='intent':intent=fixture.read_json(child/'positive-spawn-intent.json');intent['replayed']=True;overwrite(child/'positive-spawn-intent.json',intent)
                elif kind=='deadline':cli=fixture.read_json(child/'positive-cli.json');cli['elapsed']=12;overwrite(child/'positive-cli.json',cli)
                elif kind=='truncated':(child/'positive-stdout.jsonl').write_text('{')
                else:output(value,work,'positive',1,value['streams']['positive']['outputs'][1].replace('code 0','code 1'))
                with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_schema_inventory_qualification_advertisement_drift_rejected(self):
        for kind in ('schema','inventory','qualification','advertisement'):
            with tempfile.TemporaryDirectory() as directory:
                value,work,rows=evidence(pathlib.Path(directory))
                if kind=='schema':value['schema']=True
                elif kind=='inventory':value['inventory'][0]['exists']=True
                elif kind=='qualification':value['nested_cli_qualified']=True
                else:value['streams']['positive']['requests'][1]['tools'][0]['tools'].pop();sync_stream(value,work,'positive')
                with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_fixed_engine_policy_rejects_extra_mount(self):
        from tests.test_model_project_hook import policy
        binary=pathlib.Path('/binary');workspace=pathlib.Path('/workspace');cidfile=pathlib.Path('/cid');argv=control.command(binary,workspace,cidfile)
        good=policy(binary,workspace,'positive',cidfile);good['command']=argv[argv.index(control.backend.IMAGE)+1:]
        control.base.support.validate_policy(good,'a'*64,argv,binary,workspace,'created')
        good['mounts'].append(dict(Type='bind',Source='/host',Destination='/host',RW=True,Propagation='rprivate'))
        with self.assertRaises(ValueError):control.base.support.validate_policy(good,'a'*64,argv,binary,workspace,'created')

    def test_unavailable_canary_readback_remains_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory).resolve();work=root/'workspace';work.mkdir();rows=control.create_canaries(root)
            with mock.patch.object(control,'check_canaries',side_effect=OSError(errno.EIO,'fixed readback failure')):
                self.assertEqual(control.classify_incomplete(work,rows),'unknown')
            pathlib.Path(rows[0]['path']).write_bytes(b'changed')
            self.assertEqual(control.classify_incomplete(work,rows),'failed')

    def test_parent_marker_counterexample_is_saved_before_error_and_late_io(self):
        for marker in (None,'wrong'):
            for late in (False,True):
                with tempfile.TemporaryDirectory() as directory:
                    root=pathlib.Path(directory).resolve();work=root/'workspace';work.mkdir();rows=control.create_canaries(root)
                    thread='10000000-0000-4000-8000-000000000001';(work/'parent-stdout.jsonl').write_text(json.dumps({'type':'thread.started','thread_id':thread})+'\n{"unfinished":')
                    env={'CODEX_THREAD_ID':thread,'HOME':str(fixture.home('parent')),'CODEX_HOME':str(fixture.home('parent'))}
                    if marker is not None:env['NESTED_CONTROL_MARKER']=marker
                    save=fixture.write_json
                    def record(path,value):
                        self.assertEqual(str(path),'/workspace/wrapper-environment.json');save(work/path.name,value)
                        if late:raise OSError(errno.EIO,'fixed post-observation failure')
                    with mock.patch.dict(os.environ,env,clear=True),mock.patch.object(fixture.signal,'signal'),mock.patch.object(fixture.signal,'alarm'),mock.patch.object(fixture,'write_json',side_effect=record),mock.patch.object(fixture,'raw_launch',side_effect=AssertionError('CLI')):
                        with self.assertRaises(OSError if late else ValueError):fixture.wrapper()
                    self.assertEqual(control.classify_incomplete(work,rows),'failed')
                    with mock.patch.object(control,'check_canaries',side_effect=OSError(errno.EIO,'host readback')):
                        self.assertEqual(control.classify_incomplete(work,rows),'failed')

    def test_parent_marker_wrong_source_thread_or_missing_observation_is_unknown(self):
        for kind in ('source','thread','missing','schema','call','marker-field','marker-type','marker-predicate'):
            with tempfile.TemporaryDirectory() as directory:
                value,work,rows=evidence(pathlib.Path(directory));observed=fixture.read_json(work/'wrapper-environment.json');observed.update(marker='wrong',marker_matches=False)
                if kind=='source':observed['source_pin']='wrong'
                elif kind=='thread':observed['native']['CODEX_THREAD_ID']='10000000-0000-4000-8000-000000000099'
                elif kind=='schema':observed['schema']=True
                elif kind=='call':observed['call_id']='wrong'
                elif kind=='marker-field':del observed['marker']
                elif kind=='marker-type':observed['marker']=False
                elif kind=='marker-predicate':observed['marker_matches']=0
                if kind=='missing':(work/'wrapper-environment.json').rename(work/'unavailable-observation')
                else:overwrite(work/'wrapper-environment.json',observed)
                self.assertEqual(control.classify_incomplete(work,rows),'unknown')

    def test_boolean_alias_in_probe_and_journal_is_rejected(self):
        for kind in ('probe','journal'):
            with tempfile.TemporaryDirectory() as directory:
                value,work,rows=evidence(pathlib.Path(directory));child=work/'positive'
                if kind=='probe':
                    result=fixture.read_json(child/'probe.json');result['scratch']=1;overwrite(child/'probe.json',result);output(value,work,'positive',1,native(json.dumps(result)))
                else:
                    journal=control.observations(child/'probe-observations.jsonl');journal[1]['scratch']=1;(child/'probe-observations.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in journal))
                with self.assertRaises(ValueError):control.validate_evidence(value,work,rows)

    def test_probe_journal_preserves_earlier_counterexample_after_eio(self):
        for violation in ('read','same-read','marker','none'):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory).resolve();workspace=root/'workspace';workspace.mkdir();work=workspace/'positive';work.mkdir();rows=control.create_canaries(root)
                thread='10000000-0000-4000-8000-000000000002';(work/'positive-stdout.jsonl').write_text(json.dumps({'type':'thread.started','thread_id':thread})+'\n{"unfinished":')
                original_open=fixture.os.open;original_fdopen=fixture.os.fdopen;source_fds=set()
                def injected(path,flags,*args):
                    if str(path)==rows[0]['path']:
                        if violation not in ('read','same-read') or flags & os.O_WRONLY:raise OSError(errno.EIO,'fixed late observation failure')
                        fd=original_open(path,flags,*args);source_fds.add(fd);return fd
                    return original_open(path,flags,*args)
                class FailedRead:
                    def __init__(self,stream):self.stream=stream
                    def __enter__(self):return self
                    def __exit__(self,*args):self.stream.close()
                    def read(self,*args):raise OSError(errno.EIO,'fixed same-operation failure')
                def injected_fdopen(fd,*args):
                    stream=original_fdopen(fd,*args)
                    return FailedRead(stream) if violation=='same-read' and fd in source_fds else stream
                environment={'NESTED_CONTROL_MARKER':'wrong' if violation=='marker' else fixture.MARKER,'CODEX_THREAD_ID':thread}
                with mock.patch('pathlib.Path.cwd',return_value=work),mock.patch.object(fixture,'read_json',return_value=[x['path'] for x in rows]),mock.patch.object(fixture.os,'open',side_effect=injected),mock.patch.object(fixture.os,'fdopen',side_effect=injected_fdopen),mock.patch.dict(os.environ,environment,clear=True):
                    with self.assertRaises(OSError):fixture.probe()
                self.assertFalse((work/'probe.json').exists())
                self.assertEqual(control.classify_incomplete(workspace,rows),'unknown' if violation=='none' else 'failed')
                if violation!='none':
                    with (work/'probe-observations.jsonl').open('ab') as stream:stream.write(b'{"incomplete":')
                    with mock.patch.object(control,'check_canaries',side_effect=OSError(errno.EIO,'readback')):
                        self.assertEqual(control.classify_incomplete(workspace,rows),'failed')

    def test_unknown_create_and_start_never_replay(self):
        for stage in ('create','start'):
            with tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory);engine=mock.Mock();cid='a'*64
                def call(argv):
                    if argv[1]=='create':
                        (root/'cid').write_text(cid)
                        if stage=='create':raise subprocess.TimeoutExpired('create',55)
                        return cid
                    if argv[1]=='inspect':return '{}'
                    raise subprocess.TimeoutExpired('start',55)
                engine.call.side_effect=call
                with mock.patch.object(control.backend,'check_binary'),mock.patch.object(control.base.support,'validate_policy'),self.assertRaises(subprocess.TimeoutExpired):control.execute(engine,root,root/'binary',root/'workspace',[])
                self.assertEqual([x.args[0][1] for x in engine.call.call_args_list],['create','inspect'] if stage=='create' else ['create','inspect','start','inspect'])
                self.assertFalse(json.loads((root/('unknown-'+stage+'.json')).read_text())['replayed'])

    def test_captured_source_program_and_fixed_command(self):
        self.assertEqual(control.PROGRAM,'FIXTURE_SOURCE='+repr(control.SOURCE)+'\n'+control.SOURCE)
        self.assertEqual(control.command(pathlib.Path('/b'),pathlib.Path('/w'),pathlib.Path('/c'))[-1],control.PROGRAM)
        for phase in fixture.PHASES:
            argv=fixture.cli_argv(12345,phase)
            self.assertEqual('--ignore-user-config' in argv,phase=='parent')
            self.assertEqual('model="fixture-user"' in argv,False)
        with self.assertRaises(ValueError):fixture.cli_argv(True,'parent')

if __name__=='__main__':unittest.main()
