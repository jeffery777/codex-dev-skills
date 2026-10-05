"""Native intake boundary negatives; no live engine, model or host privilege changes."""
import ast
import base64
import copy
import importlib.util
import os
import pathlib
import sys
import tempfile
import time
import unittest
import zlib
from types import SimpleNamespace
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/loop-engineering/scripts'))
import model_native_checkpoint_backend as native
import model_container_launcher as launcher
import model_packet_store as packets
from tests.test_model_container_backend import FakeDocker, IMAGE
from tests.test_model_external_bootstrap import PATCH_FORMAT

spec=importlib.util.spec_from_file_location('test_native_checkpoint_host',ROOT/'scripts/verify-model-native-checkpoint.py')
host=importlib.util.module_from_spec(spec); spec.loader.exec_module(host)


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name).resolve(); self.root.chmod(0o700)
        self.files=('scripts/fixed.py',)
        self.patch=mock.patch.multiple(native,SOURCE_FILES=self.files,BINARY_BYTES=4,BINARY_SHA=packets.digest(b'stub'))
        self.patch.start(); self.addCleanup(self.patch.stop)
        for name,private in (('host',True),('guest',False)):
            tree=self.root/name; tree.mkdir(mode=0o700); (tree/'scripts').mkdir(mode=0o700)
            file=tree/'scripts/fixed.py'; file.write_bytes(b'pass\n'); file.chmod(0o600 if private else 0o444)
            if not private:
                for file,raw,mode in ((tree/'codex',b'stub',0o555),(tree/'guest-manifest.json',b'{}',0o444)):
                    file.write_bytes(raw); file.chmod(mode)
                (tree/'scripts').chmod(0o555); tree.chmod(0o555)
        fd=os.open(self.root/'capsule.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        value={'schema_version':1,'root':native.identity(os.lstat(self.root)),
            'host':native.inspect_tree(self.root/'host',self.files,private=True),
            'guest':native.inspect_tree(self.root/'guest',set(self.files)|{'codex','guest-manifest.json'},private=False)}
        with os.fdopen(fd,'wb') as stream: stream.write(packets.canonical(value))
        self.ref=native.read_file(self.root/'capsule.json',1048576,0o600)[1]

    def test_same_reference_reopens_without_recapture(self):
        first=native.validate_capsule(self.root,self.ref)
        self.assertEqual(native.validate_capsule(self.root,self.ref),first)
        self.assertEqual(first['host']['files']['scripts/fixed.py']['sha256'],first['guest']['files']['scripts/fixed.py']['sha256'])

    def test_capture_source_bytes_mode_inode_and_parent_drift_rejected(self):
        path=self.root/'host/scripts/fixed.py'; original=path.read_bytes()
        path.write_bytes(b'fail\n')
        with self.assertRaises(packets.PacketError): native.validate_capsule(self.root,self.ref)
        path.write_bytes(original)
        with self.assertRaises(packets.PacketError): native.validate_capsule(self.root,self.ref)  # Original inode metadata also bound.

    def test_guest_writable_parent_and_links_rejected(self):
        tree=self.root/'guest'; tree.chmod(0o755)
        with self.assertRaises(packets.PacketError): native.validate_capsule(self.root,self.ref)
        tree.chmod(0o555)
        path=self.root/'host/scripts/fixed.py'; os.link(path,self.root/'hardlink')
        with self.assertRaises(packets.PacketError): native.validate_capsule(self.root,self.ref)

    def test_extra_file_and_symlink_are_not_ignored(self):
        directory=self.root/'host/scripts'; (directory/'extra.py').write_bytes(b'pass\n')
        with self.assertRaises(packets.PacketError): native.inspect_tree(self.root/'host',self.files,private=True)
        (directory/'extra.py').unlink(); (directory/'fixed.py').unlink(); (directory/'fixed.py').symlink_to(self.root/'guest/scripts/fixed.py')
        with self.assertRaises(packets.PacketError): native.inspect_tree(self.root/'host',self.files,private=True)

    def test_capsule_reference_and_schema_cannot_be_repaired(self):
        ref=copy.deepcopy(self.ref); ref['sha256']='0'*64
        with self.assertRaises(packets.PacketError): native.validate_capsule(self.root,ref)
        (self.root/'capsule.json').write_bytes(b'{"schema_version":true}')
        with self.assertRaises(packets.PacketError): native.validate_capsule(self.root,self.ref)


class LauncherPolicyTests(unittest.TestCase):
    def test_unset_image_fields_support_both_docker_oci_reply_shapes(self):
        minimal={'Env':['PYTHON_VERSION=3.12.9'],'Cmd':['python3']}
        native.validate_image_config(minimal)
        native.validate_image_config({**minimal,'WorkingDir':'','User':'','OnBuild':None})
        for field in ('WorkingDir','User'):
            for value in ('/unexpected','nobody',False,0,[],{}):
                with self.subTest(field=field,value=value),self.assertRaises(packets.PacketError):
                    native.validate_image_config({**minimal,field:value})
        for field,value in (('Cmd',['python3','-c','other']),('Env',['PYTHON_VERSION=3.12.13']),
                            ('OnBuild',['RUN unexpected']),('Healthcheck',{'Test':['CMD','other']})):
            with self.subTest(field=field),self.assertRaises(packets.PacketError):
                native.validate_image_config({**minimal,field:value})

    def test_other_image_is_rejected_before_capture_or_engine_effects(self):
        engine=mock.Mock()
        with self.assertRaisesRegex(packets.PacketError,'fixed-native-checkpoint-recipe-required'):
            native.OneShotNativeFixtureBackend(SimpleNamespace(),image_id=IMAGE,endpoint='unix:///fixed.sock',
                capture_root=pathlib.Path('/unused'),capture_ref={},native_case='checkpoint',_engine=engine,opt_in=True)
        engine.assert_not_called()
        self.assertEqual(engine.mock_calls,[])

    def test_native_renderer_closed_and_same_latch_precedes_child(self):
        for case in native.CASES:
            text=launcher.render_native({},'volume','a'*64,case); parsed=ast.parse(text)
            argv=ast.literal_eval(parsed.body[1].value)
            self.assertEqual(argv,['/usr/local/bin/python3','-I','-S','-B','/fixture/scripts/model_native_checkpoint_fixture.py',case,'a'*64])
            self.assertLess(text.index("create('claim.json'"),text.index('child=os.fork()'))
            self.assertLess(text.index('os.close(control)'),text.index('libc=ctypes.CDLL'))
            self.assertNotIn('WORKER=',text)
        for case,nonce in [('arbitrary','a'*64),('checkpoint','a'*63),('checkpoint',True)]:
            with self.assertRaises(ValueError): launcher.render_native({},'volume',nonce,case)

    def test_full_native_policy_preserves_all_old_restrictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp); backend=object.__new__(native.OneShotNativeFixtureBackend)
            backend.store=SimpleNamespace(root=root,packet_id='packet'); backend.worker='noop'
            backend.native_case='checkpoint'; backend.launcher_fault='none'; backend.image_id=IMAGE
            backend.environment=['PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp']
            backend.capture_root=root/'capture'; backend._capture=lambda:None
            binding={'runtime_id':'runtime-native'}; context={'name':'volume','nonce':'a'*64}; backend.preparing={binding['runtime_id']:context}
            engine=FakeDocker(root); backend.engine=engine
            cid=engine.command(*native.containers.SyntheticContainerBackend._create_options(backend,binding)).decode()
            value=engine.inspect(cid); value['Config'].update(User='0:0',Cmd=['-I','-c',launcher.render_native(binding,'volume','a'*64,'checkpoint')])
            labels={**backend._labels(binding),'dev.codex.control':'true'}
            engine.volume=lambda _: {'Name':'volume','Driver':'local','Options':None,'Scope':'local','Labels':labels,'CreatedAt':'2026-10-05T00:00:00Z','Mountpoint':'/volume'}
            value['HostConfig'].update(CapAdd=['CAP_SETGID','CAP_SETPCAP','CAP_SETUID'],Memory=536870912,MemorySwap=536870912,PidsLimit=64,Tmpfs={'/tmp':native.TMPFS})
            value['Mounts'] += [{'Type':'volume','Name':'volume','Driver':'local','Destination':'/control','Source':'/volume','RW':True,'Propagation':''},
                {'Type':'bind','Source':backend._fixture_source(),'Destination':'/fixture','Mode':'','RW':False,'Propagation':'rprivate'}]
            value['HostConfig']['Mounts']=[{'Type':'bind','Source':str(backend._workspace(binding)),'Target':'/workspace','BindOptions':{'Propagation':'rprivate'}},
                {'Type':'volume','Source':'volume','Target':'/control','VolumeOptions':{'NoCopy':True}},
                {'Type':'bind','Source':backend._fixture_source(),'Target':'/fixture','ReadOnly':True,'BindOptions':{'Propagation':'rprivate'}}]
            backend._validate_policy(value,binding)
            for platform in ('darwin','linux'):
                with mock.patch.object(native.sys,'platform',platform):
                    literal=str(backend.capture_root/'guest')
                    source='/host_mnt'+literal if platform=='darwin' else literal
                    self.assertEqual(backend._fixture_source(),source)
                    exact=copy.deepcopy(value)
                    exact['Mounts'][-1]['Source']=source; exact['HostConfig']['Mounts'][-1]['Source']=source
                    backend._validate_policy(exact,binding)
                    for wrong in (str(backend.capture_root/'guest') if platform=='darwin' else '/host_mnt'+source,
                                  '/host_mnt'+source,source+'/../other',source+'-other'):
                        if wrong==source: continue
                        changed=copy.deepcopy(exact); changed['Mounts'][-1]['Source']=wrong
                        changed['HostConfig']['Mounts'][-1]['Source']=wrong
                        with self.subTest(platform=platform,source=wrong),self.assertRaises(packets.PacketError):
                            backend._validate_policy(changed,binding)
                    for field in ('Mounts','HostConfig'):
                        changed=copy.deepcopy(exact)
                        mounts=changed['Mounts'] if field=='Mounts' else changed['HostConfig']['Mounts']
                        mounts[-1]['Source']=source+'-other'
                        with self.subTest(platform=platform,field=field),self.assertRaises(packets.PacketError):
                            backend._validate_policy(changed,binding)
            mutations=[lambda x:x['HostConfig'].update(Memory=True),lambda x:x['HostConfig'].update(PidsLimit=32),
                lambda x:x['HostConfig'].update(Privileged=True),lambda x:x['HostConfig'].update(NetworkMode='host'),
                lambda x:x['HostConfig']['CapAdd'].append('CAP_DAC_OVERRIDE'),
                lambda x:x['HostConfig']['Mounts'][-1].update(ReadOnly=False),lambda x:x['Mounts'][-1].update(RW=True),
                lambda x:x['HostConfig']['Mounts'].append({'Target':'/secret'}),lambda x:x['Config']['Cmd'].append('unexpected')]
            for change in mutations:
                actual=copy.deepcopy(value); change(actual)
                with self.subTest(change=change),self.assertRaises(packets.PacketError): backend._validate_policy(actual,binding)

    def test_consumer_denies_every_effectful_backend_path(self):
        proxy=host.Consumer(SimpleNamespace())
        for name in ('prepare','bootstrap_input','bootstrap','launch','export_patch'):
            with self.assertRaisesRegex(packets.PacketError,'consumer-effect-denied'): getattr(proxy,name)()
        self.assertEqual(len(proxy.failures),5)

    def test_fixed_native_output_cannot_accept_generic_success(self):
        self.assertTrue(host.guest.output_valid('Exit code: 0\nWall time: 0.1 seconds\nOutput:\nSuccess. Updated the following files:\nM /workspace/example.txt\n'))
        for text in ('success','Exit code: 0\nOutput:\nok', 'Exit code: 0\nWall time: 0.1 seconds\nOutput:\nSuccess. Updated the following files:\nA /workspace/example.txt\n'):
            self.assertFalse(host.guest.output_valid(text))

    def test_original_backend_seal_cannot_bypass_native_patch_filter(self):
        backend=object.__new__(native.OneShotNativeFixtureBackend)
        with mock.patch.object(native.containers.OneShotSyntheticContainerBackend,'read_sealed_patch',return_value={'patch':b'other'}):
            with self.assertRaisesRegex(packets.PacketError,'native-checkpoint-patch-drift'):
                backend.read_sealed_patch({},1024,{})
        with mock.patch.object(native.containers.OneShotSyntheticContainerBackend,'read_sealed_patch',return_value={'patch':native.FIXED_PATCH}):
            self.assertEqual(backend.read_sealed_patch({},1024,{})['patch'],native.FIXED_PATCH)


class PacketReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name).resolve(); self.root.chmod(0o700)
        self.store=packets.PacketStore(self.root,host.PACKET); self.store.prepare('a'*64)
        with self.store.locked() as fd:
            self.store._immutable(fd,'backend-runtime-'+('b'*32)+'.patch',native.FIXED_PATCH)
        self.directory=self.root/host.PACKET

    def test_real_immutable_staging_pair_survives_reopen(self):
        first=host.packet_refs(self.store)
        self.assertEqual(host.packet_refs(packets.PacketStore(self.root,host.PACKET)),first)
        self.assertEqual(sum(r['identity'][5]==2 for r in first.values()),2)

    def test_external_third_link_and_wrong_pair_are_rejected(self):
        path=self.directory/('backend-runtime-'+('b'*32)+'.patch')
        os.link(path,self.root/'external')
        with self.assertRaisesRegex(packets.PacketError,'native-packet-file-shape'): host.packet_refs(self.store)
        (self.root/'external').unlink()
        staging=next(self.directory.glob('artifact-*')); staging.unlink(); os.link(path,self.root/'external')
        with self.assertRaisesRegex(packets.PacketError,'native-packet-hardlink-pair-drift'): host.packet_refs(self.store)

    def test_symlink_and_unknown_name_rejected(self):
        (self.directory/'extra').symlink_to(self.root/'missing')
        with self.assertRaises(packets.PacketError): host.packet_refs(self.store)

    def test_real_quarantine_reserve_snapshot_fences_old_generation(self):
        def proof(request):
            now=int(time.time())
            return {**request,'schema_version':1,'status':'isolated','external_effects':'excluded',
                'evidence_sha256':'d'*64,'observed_at':now,'expires_at':now+30}
        private=packets.PacketStore(self.root,host.PACKET,_trusted_isolation_adapters={'native':SimpleNamespace(synthetic_only=True,readback_isolation=proof)})
        value=SimpleNamespace(host_id='host',backend_id='native-fixture',policy_sha256='b'*64)
        private.reserve_runtime('attempt','e'*64,'f'*64,expected_revision=0,**host.requirements(),
            host_id=value.host_id,backend_id=value.backend_id,policy_sha256=value.policy_sha256,
            runtime_id='runtime-'+('a'*32),runtime_descriptor_required=True,runtime_bootstrap_required=True)
        ledger,old=private.supervisor_snapshot('attempt')
        ledger=private.quarantine('attempt',expected_revision=ledger['revision'],isolation_adapter_id='native')
        current=host.reserve_successor(private,value,ledger,old['binding'])
        same,successor=private.supervisor_snapshot('successor')
        self.assertEqual(same,current); self.assertEqual(successor['stage'],'reserved'); self.assertEqual(current['generation'],2)
        supervisor=host.supervisors.PacketSupervisor(private,host.Consumer(SimpleNamespace()),
            host_id=value.host_id,backend_id=value.backend_id,policy_sha256=value.policy_sha256)
        with self.assertRaisesRegex(packets.PacketError,'stale-writer-result-rejected'): supervisor.reconcile('attempt')
        self.assertIsNone(private.read_checkpoint()[0]['checkpoint'])


def observation():
    external=host.load_external(); wire=[]; thread='thread'; turn='turn'
    def row(direction,message):
        wire.append({'direction':direction,'message':message,'raw_base64':base64.b64encode(packets.canonical(message)+b'\n').decode()})
    def sent(message): row('out-intent',message); row('out-sent',message)
    def request(number,method,params,result):
        sent({'id':number,'method':method,'params':params}); row('in',{'id':number,'result':result})
    request(1,'initialize',{'clientInfo':{'name':'external_bootstrap_only','version':'1'},'capabilities':{'experimentalApi':True}}, {})
    sent({'method':'initialized'})
    start={'model':external.guest.DIRECT_MODEL,'modelProvider':'fixture','allowProviderModelFallback':False,'cwd':'/workspace',
        'ephemeral':True,'sandbox':'read-only','approvalPolicy':'never','environments':[],'experimentalRawEvents':False}
    result={'thread':{'id':thread},'model':external.guest.DIRECT_MODEL,'modelProvider':'fixture','cwd':'/workspace',
        'approvalPolicy':'never','instructionSources':[],'sandbox':{'type':'readOnly','networkAccess':False}}
    request(2,'thread/start',start,result)
    request(3,'thread/settings/update',external.settings_update_params(thread,'input-disabled-dispatch'),{})
    row('in',{'method':'thread/settings/updated','params':{'threadId':thread,'threadSettings':external.input_settings()}})
    request(4,'turn/start',host.guest.turn_params(external,thread),{'turn':{'id':turn}})
    row('in',{'method':'thread/settings/updated','params':{'threadId':thread,'threadSettings':external.input_settings(adopted=True)}})
    row('in',{'method':'turn/started','params':{'threadId':thread,'turn':{'id':turn,'status':'inProgress'}}})
    user={'type':'userMessage','id':'user','clientId':None,'content':[{'type':'text','text':'Perform the fixed anonymous fixture update.','text_elements':[]}]}
    change={'type':'fileChange','id':host.guest.CALL['call_id'],
        'changes':[{'path':'/workspace/example.txt','kind':{'type':'update','move_path':None},'diff':'@@ -1 +1 @@\n-old\n+new\n'}],'status':'inProgress'}
    agent={'type':'agentMessage','id':'native-checkpoint-final','text':'Fixed anonymous update finished.',
        'delivery':None,'memoryCitation':None,'phase':None,'questions':None}
    for item in (user,change,agent):
        row('in',{'method':'item/started','params':{'threadId':thread,'turnId':turn,'item':copy.deepcopy(item)}})
        if item is change: item=dict(item,status='completed')
        row('in',{'method':'item/completed','params':{'threadId':thread,'turnId':turn,'item':copy.deepcopy(item)}})
    row('in',{'method':'turn/completed','params':{'threadId':thread,'turn':{'id':turn,'status':'completed','error':None,'items':[agent]}}})
    output='Exit code: 0\nWall time: 0.1 seconds\nOutput:\nSuccess. Updated the following files:\nM /workspace/example.txt\n'
    initial=[{'type':'message','role':'user','content':[{'type':'input_text','text':'Perform the fixed anonymous fixture update.'}]}]
    base={'model':external.guest.DIRECT_MODEL,'stream':True,'store':False,'tool_choice':'auto','parallel_tool_calls':True,
        'tools':[{'type':'namespace','name':'functions','tools':[{'type':'custom','name':'apply_patch','format':PATCH_FORMAT}]}]}
    bodies=[dict(base,input=initial),dict(base,input=initial+[host.guest.CALL,{'type':'custom_tool_call_output','call_id':host.guest.CALL['call_id'],'output':output}])]
    receipt={'passed':True,'case':'checkpoint','nonce':'a'*64,'production_qualified':False,'thread_id':thread,'turn_id':turn,
        'client_close':{'protocol':'observed','direct_child':'exited','exit_code':0,'descendants':'unknown'},'wire':wire,
        'cli_stderr':{'raw_base64':'','captured_bytes':0,'total_bytes':0,'captured_prefix_sha256':packets.digest(b''),
            'eof':True,'overflow':False,'truncated':False,'reader_error':False,'reader_finished':True}}
    return receipt,bodies,output


def frame(receipt,bodies,output):
    receipt=copy.deepcopy(receipt); records=[]
    for stage,body in enumerate(bodies,1):
        record={'stage':stage,'response_sent':True}
        for name,raw in [('request',packets.canonical(body)),('response',host.guest.response(stage))]:
            record.update({name+'_base64':base64.b64encode(raw).decode(),name+'_bytes':len(raw),name+'_sha256':packets.digest(raw)})
        records.append(record)
    receipt['provider_bundle']=host.load_external().guest.bundle({'failed':False,'stopped':True,'slots':2,'native_output':output,'records':records})
    return host.guest.PREFIX+base64.b64encode(zlib.compress(packets.canonical(receipt)))+b'\n'


class TranscriptTests(unittest.TestCase):
    def test_complete_raw_frame_and_changed_request_hash_positive(self):
        receipt,bodies,output=observation(); raw=frame(receipt,bodies,output)
        actual=host.worker_observation(raw,{'case':'checkpoint'},{'nonce':'a'*64})
        self.assertEqual(actual['native_calls'],1)
        declarations=[host.load_external().guest.declaration(packets.canonical(b),host.load_external().base.probe.boundary,'workspace-patch') for b in bodies]
        self.assertNotEqual(declarations[0]['request_sha256'],declarations[1]['request_sha256'])
        self.assertEqual(host.guest.stable_declaration(declarations[0]),host.guest.stable_declaration(declarations[1]))
        with self.assertRaisesRegex(packets.PacketError,'native-worker-frame-shape'):
            host.worker_observation(raw.strip(),{'case':'checkpoint'},{'nonce':'a'*64})

    def test_extra_command_raw_event_wrong_params_or_missing_intent_rejected(self):
        original,bodies,output=observation()
        for kind in ('command','raw','params','intent','stderr','completion'):
            receipt=copy.deepcopy(original)
            if kind in ('command','raw'):
                message={'method':'item/started' if kind=='command' else 'rawResponseItem/completed',
                    'params':{'threadId':'thread','turnId':'turn','item':{'id':'extra','type':'commandExecution'}}}
                receipt['wire'].insert(-1,{'direction':'in','message':message,'raw_base64':base64.b64encode(packets.canonical(message)+b'\n').decode()})
            elif kind=='params':
                for row in receipt['wire']:
                    if row['message'].get('method')=='turn/start':
                        row['message']['params']['input'][0]['text']='other'; row['raw_base64']=base64.b64encode(packets.canonical(row['message'])+b'\n').decode()
            elif kind=='intent': receipt['wire'].pop(0)
            elif kind=='stderr': receipt['cli_stderr']['captured_prefix_sha256']='f'*64
            else:
                message=receipt['wire'][-1]['message']; message['params']['turn']['items'].append({'type':'commandExecution'})
                receipt['wire'][-1]['raw_base64']=base64.b64encode(packets.canonical(message)+b'\n').decode()
            with self.subTest(kind=kind),self.assertRaises((packets.PacketError,ValueError)):
                host.worker_observation(frame(receipt,bodies,output),{'case':'checkpoint'},{'nonce':'a'*64})

    def test_removed_altered_duplicate_or_extra_native_call_rejected(self):
        receipt,original,output=observation()
        for kind in ('removed','altered','duplicate','extra','model'):
            bodies=copy.deepcopy(original)
            if kind=='removed': bodies[1]['input'].pop(-2)
            elif kind=='altered': bodies[1]['input'][-2]['input']='other'
            elif kind=='duplicate': bodies[1]['input'].append(copy.deepcopy(bodies[1]['input'][-2]))
            elif kind=='extra': bodies[0]['input'].insert(0,{'type':'function_call','name':'exec_command'})
            else: bodies[1]['model']='other'
            with self.subTest(kind=kind),self.assertRaises((packets.PacketError,ValueError)):
                host.worker_observation(frame(receipt,bodies,output),{'case':'checkpoint'},{'nonce':'a'*64})


class CoordinatorTests(unittest.TestCase):
    def test_untrusted_evidence_ancestry_rejected_before_any_effect(self):
        for kind in ('writable-ancestor','symlink-ancestor','git-ancestor','relative-root','nonprivate-leaf'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp).resolve(); root.chmod(0o700)
                parent=root/'parent'; parent.mkdir(mode=0o700)
                evidence=parent/'evidence'; evidence.mkdir(mode=0o700)
                if kind=='writable-ancestor': parent.chmod(0o777)
                elif kind=='symlink-ancestor':
                    alias=root/'alias'; alias.symlink_to(parent,target_is_directory=True); evidence=alias/'evidence'
                elif kind=='git-ancestor': (parent/'.git').write_text('gitdir: irrelevant\n')
                elif kind=='relative-root': evidence=pathlib.Path('relative-evidence')
                else: evidence.chmod(0o755)
                args=SimpleNamespace(evidence_root=evidence)
                with mock.patch.object(host.tempfile,'mkdtemp') as created,\
                        mock.patch.object(host,'capture') as captured,\
                        mock.patch.object(host,'save') as saved,\
                        mock.patch.object(host.subprocess,'Popen') as started:
                    with self.assertRaises(packets.PacketError): host.run(args)
                    for effect in (created,captured,saved,started): effect.assert_not_called()

    def test_different_owner_ancestor_rejected_before_fixture_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp).resolve(); root.chmod(0o700)
            parent=root/'other-owner'; parent.mkdir(mode=0o700)
            evidence=parent/'evidence'; evidence.mkdir(mode=0o700)
            real=host.os.fstat; inode=os.stat(parent).st_ino
            def other_owner(fd):
                value=real(fd)
                if value.st_ino==inode:
                    return SimpleNamespace(st_mode=value.st_mode,st_uid=os.getuid()+1)
                return value
            with mock.patch.object(host.os,'fstat',side_effect=other_owner),\
                    mock.patch.object(host.tempfile,'mkdtemp') as created:
                with self.assertRaisesRegex(packets.PacketError,'native-private-evidence-root-untrusted'):
                    host.run(SimpleNamespace(evidence_root=evidence))
                created.assert_not_called()

    def test_private_and_root_sticky_ancestry_accept_held_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp).resolve(); root.chmod(0o700)
            with host.private_directory(root) as held:
                with host.private_directory(root,held) as reopened:
                    self.assertEqual(os.fstat(held).st_ino,os.fstat(reopened).st_ino)
                self.assertEqual(os.fstat(held).st_uid,os.getuid())
            with self.assertRaises(OSError): os.fstat(held)
        # Model the trusted sticky ancestor rule without changing host ownership.
        for mode in (0o41777,0o40755):
            packets.trust._check(SimpleNamespace(st_mode=mode,st_uid=0),directory=True,ancestor=True)
        with self.assertRaises(packets.trust.Untrusted):
            packets.trust._check(SimpleNamespace(st_mode=0o40777,st_uid=0),directory=True,ancestor=True)

    def test_coordinator_restores_caller_umask_on_success_and_early_rejection(self):
        previous = os.umask(0o022)
        self.addCleanup(os.umask, previous)
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp).resolve(); root.chmod(0o700)
            def inspect_private_mask(*args):
                active=os.umask(0o077)
                self.assertEqual(active,0o077)
                return {'passed':True}
            with mock.patch.object(host,'run_private',side_effect=inspect_private_mask):
                self.assertTrue(host.run(SimpleNamespace(evidence_root=root))['passed'])
            self.assertEqual(os.umask(0o022),0o022)
            with mock.patch.object(host,'run_private',side_effect=RuntimeError('fixed test fault')):
                with self.assertRaises(RuntimeError):
                    host.run(SimpleNamespace(evidence_root=root))
            self.assertEqual(os.umask(0o022),0o022)
            with self.assertRaises(packets.PacketError):
                host.run(SimpleNamespace(evidence_root=root/'missing'))
            self.assertEqual(os.umask(0o022),0o022)

    def test_stage_path_replacement_after_intent_prevents_process_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=pathlib.Path(tmp).resolve(); parent.chmod(0o700)
            root=parent/'evidence'; root.mkdir(mode=0o700)
            original_save=host.save
            def replace_after_intent(path,name,value):
                result=original_save(path,name,value)
                if name=='produce-intent.json':
                    root.rename(parent/'retained-original'); root.mkdir(mode=0o700)
                return result
            with host.private_directory(root) as held,\
                    mock.patch.object(host,'save',side_effect=replace_after_intent),\
                    mock.patch.object(host.subprocess,'Popen') as started:
                with self.assertRaisesRegex(packets.PacketError,'native-private-evidence-root-drift'):
                    host.run_stage(root,'produce',['never-execute'],{},5,root_fd=held)
                started.assert_not_called()

    def test_capture_final_modes_and_capsule_entries_are_synced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp).resolve(); root.chmod(0o700)
            source=root/'source'; source.mkdir(mode=0o700); (source/'scripts').mkdir(mode=0o700)
            (source/'scripts/fixed.py').write_bytes(b'import os\n')
            evidence=root/'evidence'; evidence.mkdir(mode=0o700)
            binary=root/'binary'; binary.write_bytes(b'stub'); syncs=[]; real_sync=os.fsync
            def synced(fd):
                value=os.fstat(fd); syncs.append((value.st_ino,value.st_mode)); real_sync(fd)
            external=host.load_external()
            def copy_binary(original,target): target.write_bytes(original.read_bytes()); target.chmod(0o500)
            with mock.patch.object(host,'ROOT',source),mock.patch.object(host,'load_external',return_value=external),\
                    mock.patch.object(external.base,'copy_binary',side_effect=copy_binary),\
                    mock.patch.multiple(native,SOURCE_FILES=('scripts/fixed.py',),BINARY_BYTES=4,BINARY_SHA=packets.digest(b'stub')),\
                    mock.patch.object(host.os,'fsync',side_effect=synced):
                ref=host.capture(evidence,binary); native.validate_capsule(evidence/'capsule',ref)
            for name,mode in [('guest/scripts/fixed.py',0o444),('guest/guest-manifest.json',0o444),('guest/codex',0o555),('capsule.json',0o600)]:
                value=os.lstat(evidence/'capsule'/name)
                self.assertIn((value.st_ino,value.st_mode),syncs)
                self.assertEqual(value.st_mode&0o777,mode)
            value=os.lstat(evidence/'capsule'); self.assertIn((value.st_ino,value.st_mode),syncs)

    def test_actual_stage_pid_and_wait_are_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp).resolve(); root.chmod(0o700)
            host.run_stage(root,'produce',[sys.executable,'-I','-c','import os,sys;sys.stderr.write(str(os.getpid()))'],
                {'PATH':os.defpath,'HOME':str(root),'LC_ALL':'C'},5)
            start=host.read(root,'produce-started.json'); wait=host.read(root,'produce-waited.json')
            self.assertEqual(start['pid'],wait['pid']); self.assertNotEqual(start['pid'],os.getpid())
            self.assertEqual(int(base64.b64decode(wait['stderr_base64'])),start['pid'])
            self.assertEqual(wait['exit_code'],0); self.assertTrue(wait['stderr_eof'])
