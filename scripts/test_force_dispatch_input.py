import unittest
from issue_agent import force_input_enabled

class ForceDispatchInputTests(unittest.TestCase):
    def test_boolean(self):
        self.assertTrue(force_input_enabled(True))
        self.assertFalse(force_input_enabled(False))
    def test_strings(self):
        self.assertTrue(force_input_enabled("true"))
        self.assertTrue(force_input_enabled("TRUE"))
        self.assertFalse(force_input_enabled("false"))
        self.assertFalse(force_input_enabled(""))
    def test_unexpected_values_do_not_force(self):
        for value in (None, 1, 0, [], {}):
            self.assertFalse(force_input_enabled(value))
if __name__ == "__main__":
    unittest.main()
