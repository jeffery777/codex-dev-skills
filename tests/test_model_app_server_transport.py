"""Anonymous fake subprocesses only; no native Codex, login or network."""
import json
import os
import pathlib
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'skills/loop-engineering/scripts'))
import model_app_server_transport as transport


PRELUDE = '''import json,sys,time,os
read=lambda:json.loads(sys.stdin.readline())
send=lambda x:print(json.dumps(x),flush=True)
req=read()
assert req['method']=='initialize' and 'jsonrpc' not in req
send({'id':req['id'],'result':{'userAgent':'anonymous-fixture'}})
assert read()=={'method':'initialized'}
'''
CALL = {'id': 'server-1', 'method': 'item/tool/call', 'params': {
    'arguments': {'token': 'anonymous'}, 'tool': 'packet_probe', 'callId': 'call-1',
    'threadId': 'thread-1', 'turnId': 'turn-1'}}


class TransportTests(unittest.TestCase):
    def session(self, body, *, handshake=True, callback=None, **overrides):
        limits = transport.Limits(timeout=.15, close_timeout=.02, **overrides)
        session = transport.Session([sys.executable, '-u', '-c', (PRELUDE if handshake else '') + body],
            cwd=str(pathlib.Path.cwd()), env={}, limits=limits,
            fixed_tool='packet_probe' if callback else None, tool_callback=callback)
        def cleanup():
            session.close()
            # Fixtures exit themselves; transport must never kill/relaunch them.
            session.process.wait(timeout=3)
        self.addCleanup(cleanup)
        if handshake:
            self.assertEqual(session.request('initialize', {'clientInfo': {'name': 'test', 'version': '0'}, 'capabilities': {'experimentalApi': True}}),
                {'userAgent': 'anonymous-fixture'})
        return session

    def fails(self, session, code, operation=None):
        with self.assertRaises(transport.TransportError) as raised:
            (operation or session.notification)()
        self.assertEqual(raised.exception.code, code)
        self.assertTrue(session.unknown)
        with self.assertRaises(transport.TransportError) as unavailable:
            session.request('turn/start', {})
        self.assertEqual(unavailable.exception.code, 'session_unavailable')

    def test_handshake_requests_notifications_and_optional_metadata(self):
        session = self.session("""r=read()
assert r['method']=='thread/start'
send({'method':'remoteControl/status/changed','params':{'status':'disabled'},'emittedAtMs':42})
send({'id':r['id'],'result':{'thread':{'id':'t'}}})
r=read()
assert r['method']=='account/read' and r['params']=={'refreshToken':False}
send({'id':r['id'],'result':{'account':None}})
""")
        self.assertEqual(session.request('thread/start', {}), {'thread': {'id': 't'}})
        self.assertEqual(session.notification()['method'], 'remoteControl/status/changed')
        self.assertEqual(session.request('account/read', {'refreshToken': False}), {'account': None})

    def test_fixed_tool_has_only_text_reply_and_is_observation_not_completion(self):
        seen = []
        def callback(params):
            seen.append(params)
            return {'success': True, 'contentItems': [{'type': 'inputText', 'text': 'anonymous'}]}
        session = self.session(f"send({CALL!r})\nreply=read()\nassert reply=={{'id':'server-1','result':{{'success':True,'contentItems':[{{'type':'inputText','text':'anonymous'}}]}}}}\nsend({{'method':'turn/completed','params':{{'turn':{{'status':'completed'}}}}}})\n", callback=callback)
        self.assertEqual(session.notification()['method'], 'turn/completed')
        self.assertEqual(len(seen), 1)
        self.assertFalse(session.unknown)

    def test_public_metadata_reads_do_not_admit_config_writes_or_authentication(self):
        methods = ('config/read', 'configRequirements/read',
                   'experimentalFeature/list', 'mcpServerStatus/list')
        session = self.session(f"for method in {methods!r}:\n r=read()\n assert r['method']==method\n send({{'id':r['id'],'result':{{'observation':True}}}})\n")
        # Rejected host requests must not reach the fake peer or consume an ID.
        for method in ('config/write', 'config/value/write', 'account/login/start',
                       'mcpServer/oauth/login', 'experimentalFeature/enablement/set'):
            with self.subTest(method=method), self.assertRaises(transport.TransportError) as raised:
                session.request(method, {})
            self.assertEqual(raised.exception.code, 'method_not_allowed')
        for method in methods:
            self.assertEqual(session.request(method, {}), {'observation': True})

    def test_malformed_duplicate_keys_nonfinite_and_bad_envelopes(self):
        cases = [('{oops', 'invalid_json'),
            ('{"method":"warning","method":"warning","params":{}}', 'invalid_json'),
            ('{"method":"warning","params":{"x":NaN}}', 'invalid_json'),
            ('{"method":"warning","params":{"x":1e999}}', 'invalid_json'),
            ('[]', 'invalid_envelope'),
            ('{"method":"warning","params":[]}', 'invalid_envelope'),
            ('{"method":"warning","params":{},"jsonrpc":"2.0"}', 'invalid_envelope'),
            ('{"method":"warning","params":{},"emittedAtMs":true}', 'invalid_envelope'),
            ('{"method":"new/authority","params":{}}', 'unknown_notification'),
            ('{"id":true,"result":{}}', 'uncorrelated_response'),
            ('{"id":1,"result":{},"error":{"code":0,"message":"secret"}}', 'uncorrelated_response')]
        for raw, code in cases:
            with self.subTest(raw=raw):
                session = self.session(f"print({raw!r},flush=True)")
                self.fails(session, code)

    def test_response_id_exact_type_and_association(self):
        for wrong in ('2', 999, True):
            with self.subTest(wrong=wrong):
                session = self.session(f"r=read()\nsend({{'id':{wrong!r},'result':{{}}}})")
                self.fails(session, 'uncorrelated_response', lambda: session.request('thread/read', {}))

    def test_duplicate_response_is_observed_before_next_mutation(self):
        session = self.session("r=read()\nreply={'id':r['id'],'result':{}}\nsys.stdout.write(json.dumps(reply)+'\\n'+json.dumps(reply)+'\\n');sys.stdout.flush()\nassert sys.stdin.readline()==''\n")
        self.assertEqual(session.request('thread/read', {}), {})
        self.fails(session, 'uncorrelated_response', lambda: session.request('turn/start', {}))

    def test_stalled_child_and_partial_eof_are_bounded(self):
        session = self.session("time.sleep(.4)")
        start = time.monotonic()
        self.fails(session, 'timeout')
        self.assertLess(time.monotonic() - start, .6)
        self.assertEqual(session.close(), {'protocol': 'unknown', 'direct_child': 'unknown', 'descendants': 'unknown'})
        session = self.session("sys.stdout.write('{');sys.stdout.flush()")
        self.fails(session, 'partial_eof')

    def test_eof_without_frame_is_unknown(self):
        self.fails(self.session('pass'), 'eof')

    def test_newlineless_oversize_and_total_count_queue_limits(self):
        session = self.session("sys.stdout.write('x'*500);sys.stdout.flush()", line_bytes=128)
        self.fails(session, 'line_limit')
        session = self.session("send({'method':'warning','params':{'x':'x'*80}})", total_bytes=100)
        self.fails(session, 'total_limit')
        session = self.session("send({'method':'warning','params':{}})", messages=1)
        self.fails(session, 'message_limit')
        session = self.session("r=read()\nsend({'method':'warning','params':{}})\nsend({'method':'warning','params':{}})\nsend({'id':r['id'],'result':{}})", notifications=1)
        self.fails(session, 'notification_limit', lambda: session.request('thread/read', {}))

    def test_all_known_approval_requests_deny_then_latch_unknown(self):
        for method, denial in transport.DENIALS.items():
            with self.subTest(method=method):
                request = {'id': 'approval', 'method': method, 'params': {}}
                session = self.session(f"send({request!r})\nassert read()=={{'id':'approval','result':{denial!r}}}\n")
                self.fails(session, 'approval_denied')
                session.process.wait(timeout=1)
                self.assertEqual(session.process.returncode, 0)

    def test_unknown_requests_and_wrong_tool_never_invoke_callback(self):
        callback = mock.Mock()
        for method in ('config/write', 'account/chatgptAuthTokens/refresh', 'item/tool/requestUserInput'):
            request = {'id': 'server', 'method': method, 'params': {}}
            session = self.session(f"send({request!r})", callback=callback)
            self.fails(session, 'unexpected_server_request')
        call = json.loads(json.dumps(CALL)); call['params']['tool'] = 'shell'
        session = self.session(f'send({call!r})', callback=callback)
        self.fails(session, 'invalid_tool_call')
        callback.assert_not_called()

    def test_duplicate_server_id_and_tool_call_not_replayed(self):
        for duplicate_id in (True, False):
            seen = []
            def callback(params):
                seen.append(params)
                return {'success': True, 'contentItems': []}
            call = json.loads(json.dumps(CALL))
            if not duplicate_id: call['id'] = 'server-2'
            session = self.session(f'send({CALL!r})\nread()\nsend({call!r})', callback=callback)
            self.fails(session, 'duplicate_server_id' if duplicate_id else 'duplicate_tool_call')
            self.assertEqual(len(seen), 1)

    def test_callback_exception_late_return_and_lost_reply_never_replayed(self):
        def fault(params): raise RuntimeError('credential-secret')
        session = self.session(f'send({CALL!r})', callback=fault)
        self.fails(session, 'callback_failed')
        def late(params):
            time.sleep(.2)
            return {'success': True, 'contentItems': []}
        session = self.session(f'send({CALL!r})\ntime.sleep(.3)', callback=late)
        self.fails(session, 'callback_timeout')
        calls = []
        def once(params):
            calls.append(params)
            return {'success': True, 'contentItems': []}
        session = self.session(f'send({CALL!r})\nread()\n', callback=once)
        self.fails(session, 'eof')
        self.assertEqual(len(calls), 1)

    def test_callback_bad_result_and_write_failure_are_sanitized(self):
        session = self.session(f'send({CALL!r})', callback=lambda params: {'success': 'true', 'contentItems': []})
        self.fails(session, 'invalid_tool_result')
        session = self.session('time.sleep(.3)')
        with mock.patch.object(transport.os, 'write', side_effect=BrokenPipeError('credential-secret')):
            self.fails(session, 'write_failed', lambda: session.request('turn/start', {}))

    def test_remote_error_and_stderr_payload_never_appear_in_error(self):
        session = self.session("sys.stderr.write('credential-secret'*10000);sys.stderr.flush()\nr=read()\nsend({'id':r['id'],'error':{'code':-1,'message':'credential-secret','data':{'token':'credential-secret'}}})")
        self.fails(session, 'remote_error', lambda: session.request('turn/start', {}))
        self.assertNotIn('credential-secret', repr(session.close()))

    def test_methods_and_auth_refresh_require_explicit_host_selection(self):
        session = self.session('time.sleep(.3)')
        for method, params, code in [('config/write', {}, 'method_not_allowed'),
                ('account/login/start', {}, 'method_not_allowed'), ('account/read', {}, 'auth_refresh_not_allowed'),
                ('account/read', {'refreshToken': True}, 'auth_refresh_not_allowed'),
                ('initialize', {}, 'already_initialized')]:
            with self.assertRaises(transport.TransportError) as error:
                session.request(method, params)
            self.assertEqual(error.exception.code, code)
            self.assertFalse(session.unknown)

    def test_large_write_to_nonreading_child_has_deadline(self):
        session = self.session('time.sleep(.4)')
        start = time.monotonic()
        self.fails(session, 'timeout', lambda: session.request('turn/start', {'x': 'x'*900000}))
        self.assertLess(time.monotonic() - start, .6)

    def test_preinitialize_callback_requires_host_handshake(self):
        callback = mock.Mock()
        session = self.session("import json,sys\nreq=json.loads(sys.stdin.readline())\nprint(json.dumps(" + repr(CALL) + "),flush=True)", handshake=False, callback=callback)
        self.fails(session, 'unexpected_server_request', lambda: session.request('initialize',
            {'capabilities': {'experimentalApi': True}}))
        callback.assert_not_called()

    def test_invalid_response_types_and_error_shape(self):
        for field, value, code in [('result', [], 'invalid_result'),
                ('error', {'code': True, 'message': 'secret'}, 'invalid_error')]:
            session = self.session(f"r=read()\nsend({{'id':r['id'],{field!r}:{value!r}}})")
            self.fails(session, code, lambda: session.request('thread/read', {}))

    def test_utf8_line_and_outbound_bounds(self):
        session = self.session("os.write(sys.stdout.fileno(),b'\\xff\\n')")
        self.fails(session, 'invalid_json')
        session = self.session("print('x'*129,flush=True)", line_bytes=128)
        self.fails(session, 'line_limit')
        session = self.session('time.sleep(.3)', outbound_bytes=256)
        self.fails(session, 'outbound_limit', lambda: session.request('turn/start', {'x': 'x'*300}))

    def test_invalid_limits_and_host_inputs_fail_before_launch(self):
        for values in ({'timeout': float('nan')}, {'timeout': True}, {'messages': True}, {'line_bytes': 0}):
            with self.assertRaises(ValueError): transport.Limits(**values)
        with mock.patch.object(transport.subprocess, 'Popen') as popen:
            with self.assertRaises(ValueError): transport.Session('shell string', cwd=os.getcwd(), env={})
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
