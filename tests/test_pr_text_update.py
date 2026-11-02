"""Local callback-boundary tests. No GitHub request or model execution."""
import asyncio
import copy
from dataclasses import replace
import unittest

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pr_text_update", ROOT / "scripts" / "pr_text_update.py")
assert SPEC and SPEC.loader
p = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = p
SPEC.loader.exec_module(p)


def baseline():
    return {
        "repository": "example/workflow-fixture", "repository_id": 100,
        "pr_number": 22, "pr_id": 200,
        "api_url": "https://api.github.com/repos/example/workflow-fixture/pulls/22",
        "html_url": "https://github.com/example/workflow-fixture/pull/22",
        "state": "open", "draft": True, "base_sha": "a" * 40,
        "head_sha": "b" * 40, "base_ref": "main", "head_ref": "fixture/issue-22",
        "head_repository": "example/workflow-fixture",
        "updated_at": "2026-11-02T00:00:00Z", "title": "Fixture before",
        "body": "Public fixture baseline.\n",
    }


def proposed():
    return {"repository": "example/workflow-fixture", "pr_number": 22,
            "title": "Fixture after", "body": "Public fixture update.\n"}


class Adapter:
    def __init__(self):
        self.live = baseline()
        self.calls = []
        self.checkpoints = []
        self.events = []
        self.reads = 0
        self.read_fault = None
        self.update_fault = None
        self.after_update = None
        self.during_read = None
        self.checkpoint_fault = False

    async def read(self, target):
        self.events.append("read")
        self.reads += 1
        if self.during_read:
            self.during_read()
        if self.read_fault and self.read_fault(self.reads):
            raise RuntimeError("PRIVATE_PROVIDER_ERROR_NOT_FOR_OUTPUT")
        return copy.deepcopy(self.live)

    async def checkpoint(self, record):
        self.events.append("checkpoint")
        if self.checkpoint_fault:
            raise OSError("PRIVATE_CHECKPOINT_PATH_NOT_FOR_OUTPUT")
        self.checkpoints.append(copy.deepcopy(record))

    async def update(self, arguments):
        self.events.append("update")
        self.calls.append(copy.deepcopy(arguments))
        self.live.update(title=arguments["title"], body=arguments["body"],
                         updated_at="2026-11-02T00:00:01Z")
        if self.after_update:
            self.after_update(self.live)
        if self.update_fault:
            raise self.update_fault
        return True


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = Adapter()
        self.intent = proposed()
        self.inspected = p.inspect(self.intent, baseline(), verdict="clear",
                                   inspection_reference="local-content-review")
        self.attempt = p.Attempt()

    async def send(self, intent=None):
        return await p.publish(self.inspected, self.intent if intent is None else intent,
                               read=self.adapter.read, update=self.adapter.update,
                               checkpoint=self.adapter.checkpoint, attempt=self.attempt)

    async def test_exact_single_update_and_readback(self):
        result = await self.send()
        self.assertEqual(result, p.Outcome("VERIFIED", "EXACT_READBACK"))
        self.assertEqual(self.adapter.events, ["read", "checkpoint", "update", "read"])
        self.assertEqual(self.adapter.calls, [{
            "repository_full_name": "example/workflow-fixture", "pr_number": 22,
            "title": "Fixture after", "body": "Public fixture update.\n"}])
        self.assertEqual(self.adapter.checkpoints[0]["phase"], "UNKNOWN")

    async def test_wrong_destination_and_changed_payload_never_update(self):
        for key, value in [("repository", "example/other"), ("pr_number", 23),
                           ("title", "Unreviewed title"), ("body", "Unreviewed body")]:
            with self.subTest(key=key):
                changed = dict(self.intent, **{key: value})
                result = await self.send(changed)
                self.assertEqual(result.phase, "BLOCKED")
                self.assertEqual(self.adapter.calls, [])

    async def test_unknown_mutation_fields_never_update(self):
        for key, value in [("state", "closed"), ("base_branch", "other"),
                           ("maintainer_can_modify", True), ("labels", [])]:
            with self.subTest(key=key):
                result = await self.send(dict(self.intent, **{key: value}))
                self.assertEqual(result.phase, "BLOCKED")
                self.assertEqual(self.adapter.calls, [])

    async def test_live_baseline_drift_never_update(self):
        for key, value in [("repository_id", 101), ("pr_id", 201),
                           ("pr_number", 23), ("repository", "example/other"),
                           ("title", "Other writer"), ("body", "Other writer"),
                           ("head_sha", "c" * 40), ("base_sha", "d" * 40),
                           ("head_ref", "other"), ("base_ref", "other"),
                           ("updated_at", "2026-11-02T00:00:02Z"),
                           ("draft", False), ("state", "closed"),
                           ("api_url", "https://api.github.com/repos/example/other/pulls/22"),
                           ("html_url", "https://github.com/example/other/pull/22")]:
            with self.subTest(key=key):
                self.adapter.live = dict(baseline(), **{key: value})
                result = await self.send()
                self.assertEqual(result.phase, "BLOCKED")
                self.assertEqual(self.adapter.calls, [])

    async def test_unsupported_snapshot_metadata_never_update(self):
        self.adapter.live["unknown_metadata"] = "not reviewed"
        result = await self.send()
        self.assertEqual(result.phase, "BLOCKED")
        self.assertEqual(self.adapter.calls, [])

    async def test_read_failure_never_update_and_does_not_echo_provider_error(self):
        self.adapter.read_fault = lambda _: True
        result = await self.send()
        self.assertEqual(result.phase, "BLOCKED")
        self.assertNotIn("PRIVATE", str(result))
        self.assertEqual(self.adapter.calls, [])

    async def test_checkpoint_failure_never_update(self):
        self.adapter.checkpoint_fault = True
        result = await self.send()
        self.assertEqual(result.phase, "BLOCKED")
        self.assertEqual(self.adapter.calls, [])
        self.assertNotIn("PRIVATE", str(result))

    async def test_callback_blocked_error_is_also_sanitized(self):
        async def failing_read(_):
            raise p.Blocked("PRIVATE_PROVIDER_BODY_AND_PATH")
        result = await p.publish(self.inspected, self.intent, read=failing_read,
                                 update=self.adapter.update, checkpoint=self.adapter.checkpoint,
                                 attempt=self.attempt)
        self.assertEqual(result, p.Outcome("BLOCKED", "CHECK_FAILED"))
        self.assertEqual(self.adapter.calls, [])

    async def test_caller_input_changed_during_read_uses_inspected_frozen_text(self):
        self.adapter.during_read = lambda: self.intent.update(body="Changed after validation")
        result = await self.send()
        self.assertEqual(result.phase, "VERIFIED")
        self.assertEqual(self.adapter.calls[0]["body"], "Public fixture update.\n")

    async def test_inspection_object_cannot_silently_be_rebound(self):
        self.inspected = replace(self.inspected, binding="0" * 64)
        result = await self.send()
        self.assertEqual(result.phase, "BLOCKED")
        self.assertEqual(self.adapter.calls, [])

    async def test_success_cannot_be_resent(self):
        await self.send()
        result = await self.send()
        self.assertEqual(result.phase, "BLOCKED")
        self.assertEqual(len(self.adapter.calls), 1)

    async def test_same_attempt_concurrent_publish_reserves_before_first_await(self):
        entered, release = asyncio.Event(), asyncio.Event()
        count = 0

        async def held_read(target):
            nonlocal count
            count += 1
            captured = copy.deepcopy(self.adapter.live)
            if count == 1:
                entered.set()
                await release.wait()
            return captured

        async def invoke():
            return await p.publish(self.inspected, self.intent, read=held_read,
                                   update=self.adapter.update, checkpoint=self.adapter.checkpoint,
                                   attempt=self.attempt)

        first = asyncio.create_task(invoke())
        await asyncio.wait_for(entered.wait(), timeout=1)
        try:
            second_result = await asyncio.wait_for(invoke(), timeout=1)
        finally:
            release.set()
        first_result = await asyncio.wait_for(first, timeout=1)
        self.assertEqual(len(self.adapter.calls), 1)
        self.assertEqual(first_result.phase, "VERIFIED")
        self.assertEqual(second_result.phase, "BLOCKED")

    async def test_applied_but_lost_response_is_unknown_then_read_only_reconcile(self):
        self.adapter.update_fault = TimeoutError("PRIVATE_PROVIDER_ERROR")
        result = await self.send()
        self.assertEqual(result.phase, "UNKNOWN")
        self.assertEqual(self.attempt.phase, "UNKNOWN")
        self.assertEqual(len(self.adapter.calls), 1)
        again = await self.send()
        self.assertEqual(again.phase, "BLOCKED")
        observed = await p.reconcile(self.inspected, read=self.adapter.read)
        self.assertEqual(observed, p.Outcome("OBSERVED", "DESIRED_TEXT_PRESENT_AFTER_UNKNOWN"))
        self.assertEqual(len(self.adapter.calls), 1)
        self.assertNotIn("PRIVATE", str(result))

    async def test_unknown_without_application_does_not_authorize_resend(self):
        async def no_application(args):
            self.adapter.calls.append(args)
            raise TimeoutError()
        result = await p.publish(self.inspected, self.intent, read=self.adapter.read,
                                 update=no_application, checkpoint=self.adapter.checkpoint,
                                 attempt=self.attempt)
        self.assertEqual(result.phase, "UNKNOWN")
        observed = await p.reconcile(self.inspected, read=self.adapter.read)
        self.assertEqual(observed.phase, "UNKNOWN")
        self.assertEqual((await self.send()).phase, "BLOCKED")
        self.assertEqual(len(self.adapter.calls), 1)

    async def test_non_success_callback_is_unknown(self):
        async def unclear(args):
            self.adapter.calls.append(args)
            return {"isError": False}  # Native bridge must explicitly verify its result.
        result = await p.publish(self.inspected, self.intent, read=self.adapter.read,
                                 update=unclear, checkpoint=self.adapter.checkpoint,
                                 attempt=self.attempt)
        self.assertEqual(result.phase, "UNKNOWN")
        self.assertEqual(len(self.adapter.calls), 1)

    async def test_readback_failure_is_unknown_and_no_resend(self):
        self.adapter.read_fault = lambda n: n > 1
        result = await self.send()
        self.assertEqual(result.phase, "UNKNOWN")
        self.assertEqual((await self.send()).phase, "BLOCKED")
        self.assertEqual(len(self.adapter.calls), 1)

    async def test_readback_identity_or_text_mismatch_is_unknown(self):
        for key, value in [("title", "Third party"), ("body", "Third party"),
                           ("pr_id", 299), ("repository_id", 199),
                           ("html_url", "https://github.com/example/other/pull/22"),
                           ("head_sha", "c" * 40), ("state", "closed")]:
            with self.subTest(key=key):
                self.adapter = Adapter()
                self.attempt = p.Attempt()
                self.adapter.after_update = lambda live: live.update({key: value})
                result = await self.send()
                self.assertEqual(result.phase, "UNKNOWN")
                self.assertEqual(len(self.adapter.calls), 1)

    async def test_reconciliation_failure_has_no_update_path(self):
        self.adapter.read_fault = lambda _: True
        result = await p.reconcile(self.inspected, read=self.adapter.read)
        self.assertEqual(result.phase, "UNKNOWN")
        self.assertEqual(self.adapter.calls, [])

    async def test_cancellation_leaves_durable_unknown_before_callback(self):
        async def cancelled(args):
            self.adapter.calls.append(args)
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await p.publish(self.inspected, self.intent, read=self.adapter.read,
                            update=cancelled, checkpoint=self.adapter.checkpoint,
                            attempt=self.attempt)
        self.assertEqual(self.adapter.checkpoints[0]["phase"], "UNKNOWN")
        self.assertEqual(self.attempt.phase, "UNKNOWN")
        self.assertEqual((await self.send()).phase, "BLOCKED")

    async def test_stale_baseline_after_fresh_inspection_requires_another_inspection(self):
        self.adapter.live["title"] = "New legitimate title"
        self.assertEqual((await self.send()).phase, "BLOCKED")
        self.inspected = p.inspect(self.intent, self.adapter.live, verdict="clear",
                                   inspection_reference="fresh-content-review")
        self.assertEqual((await self.send()).phase, "VERIFIED")

    async def test_body_bytes_are_not_normalized(self):
        for text in ["line\n", "line\r\n", "é", "e\u0301", "line "]:
            with self.subTest(text=text):
                self.adapter = Adapter()
                self.attempt = p.Attempt()
                self.intent["body"] = text
                self.inspected = p.inspect(self.intent, baseline(), verdict="clear",
                                           inspection_reference="exact-byte-review")
                self.assertEqual((await self.send()).phase, "VERIFIED")
                self.assertEqual(self.adapter.calls[0]["body"], text)


class InputTests(unittest.TestCase):
    def test_declared_rest_metadata_mapping(self):
        b = baseline()
        raw = {"base": {"repo": {"full_name": b["repository"], "id": b["repository_id"]},
                         "sha": b["base_sha"], "ref": b["base_ref"]},
               "head": {"repo": {"full_name": b["head_repository"]},
                         "sha": b["head_sha"], "ref": b["head_ref"]},
               "id": b["pr_id"], "number": b["pr_number"], "url": b["api_url"],
               "html_url": b["html_url"], "state": b["state"], "draft": b["draft"],
               "updated_at": b["updated_at"], "title": b["title"], "body": b["body"],
               "uninspected_provider_metadata": "not claimed as reviewed"}
        self.assertEqual(p.normalize_rest_pull(raw), b)
        del raw["base"]["repo"]["id"]
        with self.assertRaises(p.Blocked):
            p.normalize_rest_pull(raw)

    def test_strict_json_rejects_duplicates_nonfinite_encoding_and_size(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}',
                    b'"\xff"', b'[' * 2000, b' ' * (p.MAX_INPUT_BYTES + 1)]:
            with self.subTest(raw=raw[:30]):
                with self.assertRaises(p.Blocked):
                    p.strict_json(raw)

    def test_invalid_ids_and_unsupported_fields(self):
        for value in [True, 0, -1, 2**53, "22"]:
            with self.assertRaises(p.Blocked):
                p.request(dict(proposed(), pr_number=value))
        for key in ["labels", "state", "base_branch", "maintainer_can_modify"]:
            with self.assertRaises(p.Blocked):
                p.request(dict(proposed(), **{key: "unreviewed"}))

    def test_invalid_titles_and_bodies(self):
        for value in ["", "a\nb", "a\x00b", "a" * 257, "\ud800", None]:
            with self.assertRaises(p.Blocked):
                p.request(dict(proposed(), title=value))
        for value in [None, "\x00", "\ud800", "x" * (p.MAX_BODY_BYTES + 1)]:
            with self.assertRaises(p.Blocked):
                p.request(dict(proposed(), body=value))

    def test_inspection_requires_clear_prior_content_review(self):
        for verdict in ["NOT_RUN", "BLOCKED", "unknown", ""]:
            with self.assertRaises(p.Blocked):
                p.inspect(proposed(), baseline(), verdict=verdict, inspection_reference="review")
        with self.assertRaises(p.Blocked):
            p.inspect(proposed(), baseline(), verdict="clear", inspection_reference="")

    def test_destination_must_match_inspected_baseline(self):
        with self.assertRaises(p.Blocked):
            p.inspect(dict(proposed(), repository="example/other"), baseline(),
                      verdict="clear", inspection_reference="review")


if __name__ == "__main__":
    unittest.main(verbosity=2)
