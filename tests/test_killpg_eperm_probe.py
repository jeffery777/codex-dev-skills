from __future__ import annotations

import argparse
import errno
import importlib.util
import pathlib
import signal
import time
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts/diagnostics/killpg_eperm_probe.py"
SPEC = importlib.util.spec_from_file_location("killpg_diagnostic", SCRIPT)
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)


class KillpgDiagnosticTests(unittest.TestCase):
    def test_deferred_observer_preserves_exception_without_extra_identity_calls(self):
        failure = PermissionError(errno.EPERM, "synthetic denial")
        operation = mock.Mock(side_effect=failure)
        events = []
        with mock.patch.object(diagnostic, "identity") as identity:
            with self.assertRaises(PermissionError) as raised:
                diagnostic.signal_call(12345, signal.SIGTERM, events,
                                       time.monotonic_ns(), operation, defer_details=True)
        self.assertIs(failure, raised.exception)
        identity.assert_not_called()
        operation.assert_called_once_with(12345, signal.SIGTERM)
        self.assertIs(failure, events[0]["_exception"])
        self.assertNotIn("exception", events[0])

    def test_minimal_eof_observes_real_fixed_child_without_adapter(self):
        args = argparse.Namespace(child_metadata=True, case="eof", delay=0, signal="zero")
        result = diagnostic.minimal_trial(args)
        self.assertEqual(8192, result["read_bytes"])
        self.assertTrue(result["read_to_eof"])
        self.assertEqual(0, result["returncode"])
        self.assertEqual(result["child_pid"], result["child_metadata"]["pid"])
        self.assertEqual(result["child_pid"], result["child_metadata"]["pgid"])
        self.assertEqual(result["child_pid"], result["child_metadata"]["sid"])
        self.assertIsNone(result["receipt"])
        event = result["events"][0]
        self.assertEqual(result["child_pid"], event["target_pgid"])
        self.assertLessEqual(result["read_complete_ns"], event["before_ns"])
        self.assertLessEqual(event["after_ns"], result["wait_return_ns"])
        if "exception" in event:
            self.assertIn("Traceback", event["exception"]["traceback"])
            self.assertIn(event["exception"]["errno"], [errno.EPERM, errno.ESRCH])
        else:
            self.assertEqual("permitted", event["result"])


if __name__ == "__main__":
    unittest.main()
