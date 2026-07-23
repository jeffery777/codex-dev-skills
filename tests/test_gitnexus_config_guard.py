from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-gitnexus-config.py"
SPEC = importlib.util.spec_from_file_location("validate_gitnexus_config", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class GitNexusConfigGuardTests(unittest.TestCase):
    def write(self, root: pathlib.Path, value: object) -> pathlib.Path:
        path = root / ".gitnexusrc"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_repository_config_is_exact_and_valid(self) -> None:
        result = VALIDATOR.validate(ROOT / ".gitnexusrc")
        self.assertEqual("valid", result["status"])
        self.assertIs(True, result["index_only"])

    def test_missing_malformed_and_duplicate_config_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            with self.assertRaisesRegex(VALIDATOR.GitNexusConfigError, "missing"):
                VALIDATOR.validate(root / ".gitnexusrc")

            path = root / ".gitnexusrc"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.GitNexusConfigError, "valid JSON"):
                VALIDATOR.validate(path)

            path.write_text(
                '{"analyze":{"indexOnly":true,"indexOnly":true}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(VALIDATOR.GitNexusConfigError, "duplicate"):
                VALIDATOR.validate(path)

    def test_unknown_or_weakened_fields_fail_closed(self) -> None:
        cases = (
            ({"analyze": {"indexOnly": False}}, "must be true"),
            ({"analyze": {"indexOnly": "true"}}, "must be true"),
            ({"analyze": {"indexOnly": True, "skipAgentsMd": True}}, "only indexOnly"),
            ({"analyze": {"indexOnly": True}, "name": "unsafe"}, "only the analyze"),
            ({"indexOnly": True}, "only the analyze"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            for document, message in cases:
                with self.subTest(document=document):
                    path = self.write(root, document)
                    with self.assertRaisesRegex(VALIDATOR.GitNexusConfigError, message):
                        VALIDATOR.validate(path)

    def test_symlink_and_oversized_config_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            target = root / "target"
            target.write_text('{"analyze":{"indexOnly":true}}', encoding="utf-8")
            link = root / ".gitnexusrc"
            link.symlink_to(target)
            with self.assertRaisesRegex(VALIDATOR.GitNexusConfigError, "non-symlink"):
                VALIDATOR.validate(link)

            link.unlink()
            link.write_text(" " * (VALIDATOR.MAX_CONFIG_BYTES + 1), encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.GitNexusConfigError, "size limit"):
                VALIDATOR.validate(link)


if __name__ == "__main__":
    unittest.main()
