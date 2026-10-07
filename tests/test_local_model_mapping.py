from __future__ import annotations
import copy
import datetime as dt
import json
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
import local_model_mapping as mapping
import profile_preflight as profiles
import agent_routing as routing
import loopctl


class LocalMappingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform == 'darwin' else None)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.home = self.root/'home'; self.home.mkdir(mode=0o700)
        self.destination = self.home/'role-models'; self.destination.mkdir(mode=0o700)
        self.env = mock.patch.dict(os.environ, {'CODEX_HOME':str(self.home)})
        self.env.start()
        self.role = 'loop_v2a_balanced_worker'
        _,self.entries = profiles.validate(ROOT/'agent-profiles')
        entry = self.entries[self.role]
        raw = (ROOT/'agent-profiles'/entry['file']).read_text().replace('"gpt-6.1-sol"','"synthetic-worker"').replace('"medium"','"low"')
        self.profile = self.destination/entry['file']; self.profile.write_text(raw)
        self.evidence = self.home/'quality.txt'; self.evidence.write_text('Synthetic oracle only, no production qualification.')
        self.record = {'role':self.role, 'runtime':'cli', 'provider_id':'synthetic-provider', 'provider_config_sha256':'a'*64,
                       'model':'synthetic-worker','reasoning_effort':'low','base_profile_sha256':entry['_profile_digest'],
                       'profile':'role-models/'+entry['file'], 'profile_sha256':mapping.digest(raw.encode()),
                       'capability_class':entry['capability_class'],'capability_tier':entry['capability_tier'],
                       'task_scopes':['fixture-repair'],'quality_evidence':'quality.txt','quality_evidence_sha256':mapping.digest(self.evidence.read_bytes()),
                       'expires_on':None,'enabled':True}
        self.context = {'schema_version':1, 'model':'synthetic-worker', 'runtime':'cli', 'provider_config_sha256':'a'*64,
                        'backend_context_window':16000,'backend_max_input_tokens':14000,'backend_max_output_tokens':2000,
                        'reserved_output_tokens':1000,'reserved_reasoning_tokens':500,'safety_margin_tokens':1000,
                        'model_context_window':16000,'model_auto_compact_token_limit':12000,'model_catalog_sha256':'c'*64,
                        'capacity_evidence':'quality.txt','capacity_evidence_sha256':mapping.digest(self.evidence.read_bytes())}
        self.context_file = self.home/'context.json';self.context_file.write_text(json.dumps(self.context))
        self.record.update(context_policy='context.json',context_policy_sha256=mapping.digest(self.context_file.read_bytes()))
        self.store = {'schema_version':1,'enabled':True,'mappings':[self.record]}
        self.facts = {'custom_agent_surface':'available','available_models':['synthetic-worker'],
                      'reasoning_efforts':{'synthetic-worker':['low']},'parent_sandbox_mode':'workspace-write',
                      'model_surface':{'runtime':'cli','source':'synthetic schema','observed_on':dt.date.today().isoformat()},
                      'local_model_surface':{'runtime':'cli','provider_id':'synthetic-provider','provider_config_sha256':'a'*64,'supported_roles':[self.role],'context_metadata':{'synthetic-worker':{k:self.context[k] for k in ['model_context_window','model_auto_compact_token_limit','model_catalog_sha256']}}},
                      'parent_default':{'available':True,'capability_classes':['balanced-worker'],'capability_tiers':{'balanced-worker':['everyday']}},
                      'sequential':{'available':True,'capability_classes':['balanced-worker'],'capability_tiers':{'balanced-worker':['everyday']}}}
        self.write_store()

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def write_store(self):
        (self.home/mapping.STORE).write_text(json.dumps(self.store))

    def resolve(self):
        return mapping.resolve(role=self.role,entries=self.entries,facts=self.facts,scope='fixture-repair',destination=self.destination,profile_dir=ROOT/'agent-profiles')

    def route(self):
        factors = {'ambiguity':'moderate','reasoning_depth':'balanced','code_context_volume':'medium','security_data_migration_public_contract_risk':'routine','write_blast_radius':'bounded','latency_sensitivity':'medium','cost_token_sensitivity':'medium','independence_parallelizability':'independent','verification_burden':'medium'}
        payload = {'contract_version':2,'task':{'id':'S1','workload_kind':'implementation','qualification_scope':'fixture-repair','factors':factors},
                   'profile_preflight':{'profile_dir':str(ROOT/'agent-profiles'),'registry':str(loopctl.CANONICAL_PROFILE_REGISTRY),'role':self.role,'agent_roots':[],'destination_root':str(self.destination)},
                   'assignment':{'scope':['fixture.txt'],'ownership':{'owner':'synthetic','disjoint':True},'source_revision':{'branch':'synthetic','head_sha':'a'*40},'authority_contract':{'external_write':False}}}
        p=self.root/'route.json'; p.write_text(json.dumps(payload))
        f=self.root/'facts.json'; f.write_text(json.dumps(self.facts))
        out=StringIO()
        with redirect_stdout(out): code=loopctl.command_agent_route(p,runtime_facts_path=f)
        return code,json.loads(out.getvalue())

    def test_absent_disabled_keep_baseline(self):
        self.store['enabled']=False;self.write_store(); self.assertIsNone(self.resolve())
        (self.home/mapping.STORE).unlink(); self.assertIsNone(self.resolve())

    def test_absent_store_does_not_check_repository_home(self):
        (self.home/mapping.STORE).unlink();(self.home/'.git').mkdir()
        self.assertIsNone(self.resolve())

    def test_context_unknown_unsafe_and_runtime_drift_fail_closed(self):
        original=copy.deepcopy(self.context)
        for key,value in [('backend_context_window',None),('model_auto_compact_token_limit',15000),('reserved_output_tokens',3000),('model_context_window',999999)]:
            with self.subTest(key=key):
                self.context=copy.deepcopy(original);self.context[key]=value
                self.context_file.write_text(json.dumps(self.context));self.record['context_policy_sha256']=mapping.digest(self.context_file.read_bytes());self.write_store()
                code,result=self.route();self.assertEqual(2,code,result)
        self.context=original;self.context_file.write_text(json.dumps(original));self.record['context_policy_sha256']=mapping.digest(self.context_file.read_bytes());self.write_store()
        self.facts['local_model_surface']['context_metadata']['synthetic-worker']['model_catalog_sha256']='b'*64
        self.assertEqual(2,self.route()[0])

    def test_nested_context_json_is_structurally_rejected(self):
        self.context_file.write_text('['*15000+']'*15000)
        self.record['context_policy_sha256']=mapping.digest(self.context_file.read_bytes());self.write_store()
        code,result=self.route();self.assertEqual(2,code,result);self.assertEqual('human-gate',result['status'])

    def test_two_mapped_roles_share_destination(self):
        role='loop_v2a_routine_reviewer';entry=self.entries[role]
        raw=(ROOT/'agent-profiles'/entry['file']).read_text().replace('"gpt-6.1-sol"','"synthetic-worker"').replace('"high"','"low"')
        (self.destination/entry['file']).write_text(raw)
        record={**self.record,'role':role,'profile':'role-models/'+entry['file'],'profile_sha256':mapping.digest(raw.encode()),
                'base_profile_sha256':entry['_profile_digest'],'capability_class':entry['capability_class'],'capability_tier':entry['capability_tier']}
        self.store['mappings'].append(record);self.facts['local_model_surface']['supported_roles'].append(role);self.write_store()
        self.assertEqual(0,self.route()[0])
        (self.destination/entry['file']).write_text(raw+'# drift')
        self.assertEqual(2,self.route()[0])

    def test_effective_mapping_preserves_contract_and_receipt(self):
        entry,binding,_=self.resolve()
        self.assertEqual('synthetic-worker',entry['runtime_mapping']['model'])
        self.assertEqual('everyday',entry['capability_tier'])
        code,result=self.route();self.assertEqual(0,code,result)
        receipt=result['route_receipt']; self.assertTrue(routing.validate_route_receipt(receipt)['valid'])
        self.assertEqual(binding,receipt['config_evidence']['local_model_mapping'])
        bad=copy.deepcopy(receipt);bad['config_evidence']['local_model_mapping']['profile_sha256']='b'*64
        bad['config_evidence_sha256']=routing._digest(bad['config_evidence']);bad['route_receipt_id']=routing._digest({k:v for k,v in bad.items() if k!='route_receipt_id'})
        self.assertIn('local-model-mapping-binding-mismatch',routing.validate_route_receipt(bad)['issues'])

    def test_invalid_or_unavailable_never_falls_back(self):
        changes=[('runtime-shape',lambda:self.facts['local_model_surface'].update(runtime=['bad'])),
                 ('provider-shape',lambda:self.facts['local_model_surface'].update(provider_id=['bad'])),
                 ('context-entry-shape',lambda:self.facts['local_model_surface']['context_metadata'].update({'synthetic-worker':['bad']})),
                 ('context-shape',lambda:self.facts['local_model_surface'].update(context_metadata=['bad'])),
                 ('provider',lambda:self.facts['local_model_surface'].update(provider_id='other')),
                 ('runtime',lambda:self.facts['local_model_surface'].update(runtime='desktop')),
                 ('role',lambda:self.facts['local_model_surface'].update(supported_roles=[])),
                 ('model',lambda:self.facts.update(available_models=[])),
                 ('effort',lambda:self.facts.update(reasoning_efforts={'synthetic-worker':['high']})),
                 ('sandbox',lambda:self.facts.update(parent_sandbox_mode='read-only')),
                 ('revoked',lambda:self.record.update(enabled=False)),
                 ('expired',lambda:self.record.update(expires_on='2000-01-01')),
                 ('scope',lambda:self.record.update(task_scopes=['other'])),
                 ('tier',lambda:self.record.update(capability_tier='deep')),
                 ('base',lambda:self.record.update(base_profile_sha256='b'*64))]
        original_facts=copy.deepcopy(self.facts);original_record=copy.deepcopy(self.record)
        for label,change in changes:
            with self.subTest(label=label):
                self.facts=copy.deepcopy(original_facts);self.record.clear();self.record.update(original_record)
                change();self.write_store();code,result=self.route()
                self.assertEqual(2,code,result);self.assertEqual('human-gate',result['status'])
                self.assertNotIn('route_receipt',result)

    def test_profile_and_quality_drift_rejected(self):
        for path in [self.profile,self.evidence]:
            original=path.read_bytes();path.write_bytes(original+b'\nchanged')
            with self.assertRaises(mapping.MappingError):self.resolve()
            path.write_bytes(original)
        self.profile.write_text(self.profile.read_text().replace('workspace-write','read-only'))
        self.record['profile_sha256']=mapping.digest(self.profile.read_bytes());self.write_store()
        with self.assertRaisesRegex(mapping.MappingError,'contract-modified'):self.resolve()

    def test_untrusted_duplicate_and_repo_store_rejected(self):
        for raw in [json.dumps(self.store).replace('"enabled": true','"enabled": true, "enabled": true',1), '{"schema_version":1,"enabled":true,"mappings":[],"extra":1}']:
            (self.home/mapping.STORE).write_text(raw)
            with self.assertRaises(mapping.MappingError):self.resolve()
        self.write_store();(self.home/mapping.STORE).chmod(0o666)
        with self.assertRaises(mapping.MappingError):self.resolve()
        (self.home/mapping.STORE).chmod(0o600);(self.home/'.git').mkdir()
        with self.assertRaises(mapping.MappingError):self.resolve()

    def test_installer_preserves_mapping_destination(self):
        with self.assertRaisesRegex(mapping.MappingError,'preserved'):mapping.installer_check(self.destination)
        mapping.installer_check(self.home/'agents')
        self.store['enabled']=False;self.write_store();mapping.installer_check(self.destination)

    def test_symlink_path_and_traversal_rejected(self):
        self.evidence.unlink();self.evidence.symlink_to(self.profile)
        with self.assertRaises(mapping.MappingError):self.resolve()
        self.record['quality_evidence']='../other';self.write_store()
        with self.assertRaises(mapping.MappingError):self.resolve()

    def test_integration_rechecks_binding_and_rejects_malformed_receipts(self):
        from tests.test_loopctl import agent_integration_document
        code,result=self.route();self.assertEqual(0,code)
        receipt=result['route_receipt']
        artifacts=self.root/'artifacts';artifacts.mkdir()
        verification=self.root/'verify';verification.mkdir()
        (artifacts/'result.txt').write_text('synthetic output')
        (verification/'check.txt').write_text('synthetic check')
        document=agent_integration_document(receipt,artifact='result.txt',artifact_digest=mapping.digest((artifacts/'result.txt').read_bytes()),
                                            verification_artifact='check.txt',verification_digest=mapping.digest((verification/'check.txt').read_bytes()))
        path=self.root/'integration.json';facts_path=self.root/'facts.json'
        def integrate(doc,with_facts=True):
            path.write_text(json.dumps(doc));facts_path.write_text(json.dumps(self.facts));out=StringIO()
            with redirect_stdout(out),mock.patch.object(loopctl,'_current_git_revision',return_value=receipt['source_revision']):
                code=loopctl.command_agent_integrate(path,repo_root=ROOT,artifact_root=artifacts,verification_root=verification,
                                                    assignment_fresh=True,profile_path=self.profile,profile_dir=ROOT/'agent-profiles',
                                                    runtime_facts_path=facts_path if with_facts else None)
            return code,json.loads(out.getvalue())
        self.assertEqual(0,integrate(document)[0])
        self.assertEqual(1,integrate(document,False)[0])
        for mutation in [lambda r:r['config_evidence']['local_model_mapping'].pop('role'),lambda r:r.update(profile_selection=['malformed'])]:
            bad=copy.deepcopy(document);mutation(bad['agent_integration']['route_receipt'])
            code,result=integrate(bad);self.assertEqual(1,code,result);self.assertEqual('rejected',result['status'])
        for key,value in [('enabled',False),('base_profile_sha256','b'*64)]:
            before=self.record[key];self.record[key]=value;self.write_store()
            self.assertEqual(1,integrate(document)[0]);self.record[key]=before;self.write_store()
        self.facts['local_model_surface']['context_metadata']['synthetic-worker']['model_auto_compact_token_limit']=15000
        self.assertEqual(1,integrate(document)[0])

    def test_removal_revocation_changes_binding(self):
        _,binding,_=self.resolve();self.record['enabled']=False;self.write_store()
        with self.assertRaises(mapping.MappingError):self.resolve()
        self.record['enabled']=True;self.record['expires_on']='9999-12-31';self.write_store()
        self.assertNotEqual(binding,self.resolve()[1])


if __name__=='__main__':unittest.main()
