import unittest
from control import label

class LocalChecks(unittest.TestCase):
    def test_label(self):
        self.assertEqual("Result: sample", label("sample"))

    def test_result_is_string(self):
        self.assertIsInstance(label("sample"), str)

    @unittest.skip("remote publishing is outside this offline packet")
    def test_remote_publish(self):
        raise AssertionError("never access a remote service")

if __name__ == "__main__":
    unittest.main(verbosity=2)
